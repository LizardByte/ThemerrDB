/**
 * @file Handles issue comment commands for ThemerrDB moderation workflows.
 */

const fs = require('node:fs')
const path = require('node:path')

const {queueIssueForApproval} = require('./approval-queue.js')
const {
  delay,
  issueParams,
  labelNames,
  removeLabelsByName,
  repoParams
} = require('./github-issue.js')

const ADMIN_REPOSITORY_PERMISSION = 'admin'
const ALL_COMMANDS = '*'
const AUTO_APPROVED_USERS_FILE = 'auto_approved_users.json'
const BOT_COMMAND_PREFIX = '@LizardByte-bot'
const KNOWN_COMMANDS = new Set(['approve', 'check', 'edit', 'question'])
const NORMALIZABLE_PRIMITIVE_TYPES = new Set(['bigint', 'number', 'string'])
const QUESTION_LABEL = 'question'
const REQUEST_THEME_LABEL = 'request-theme'

/**
 * Normalize a command comment before parsing positional arguments.
 *
 * @param {string} commentBody Raw issue comment body.
 * @returns {string} Trimmed comment with repeated spaces collapsed.
 */
function normalizeComment(commentBody) {
  let comment = `${commentBody}`.trim()

  do {
    comment = comment.replace('  ', ' ')
  } while (comment.includes('  '))

  return comment
}

/**
 * Parse a normalized comment into a command and positional arguments.
 *
 * @param {string} comment Normalized issue comment body.
 * @returns {{command: string, args: string[]}} Parsed command details.
 */
function parseCommandComment(comment) {
  const args = comment.split(' ')
  if (args[0] === BOT_COMMAND_PREFIX) {
    return {
      command: normalizeCommandName(args[1]),
      args
    }
  }

  if (args[0].startsWith('/')) {
    return {
      command: normalizeCommandName(args[0].slice(1)),
      args
    }
  }

  return {
    command: '',
    args: []
  }
}

/**
 * Normalize a GitHub user id for matching.
 *
 * @param {*} userId GitHub user id.
 * @returns {string} Trimmed user id string.
 */
function normalizeUserId(userId) {
  if (!NORMALIZABLE_PRIMITIVE_TYPES.has(typeof userId)) {
    return ''
  }

  return String(userId).trim()
}

/**
 * Normalize a command name for matching.
 *
 * @param {*} command Bot command name.
 * @returns {string} Lowercase command name.
 */
function normalizeCommandName(command) {
  if (!NORMALIZABLE_PRIMITIVE_TYPES.has(typeof command)) {
    return ''
  }

  return String(command).trim().toLowerCase()
}

/**
 * Normalize a configured command list.
 *
 * @param {object} commands Configured command list.
 * @returns {Set<string>} Normalized command names.
 */
function normalizeAllowedCommands(commands) {
  if (!Array.isArray(commands)) {
    return new Set()
  }

  return new Set(commands.map(normalizeCommandName).filter(Boolean))
}

/**
 * Resolve a trusted users file inside the current workspace.
 *
 * @param {string} trustedUsersFile Trusted users file path.
 * @returns {string} Absolute trusted users file path.
 */
function resolveTrustedUsersFile(trustedUsersFile) {
  const baseDir = process.cwd()
  const resolvedFile = path.resolve(baseDir, trustedUsersFile)
  const relativePath = path.relative(baseDir, resolvedFile)

  if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
    throw new Error('trusted command users file must be inside the working directory')
  }

  return resolvedFile
}

/**
 * Load trusted command users from the configured JSON file.
 *
 * @param {object} [options] Loader options.
 * @param {string} [options.trustedUsersFile] Trusted users file path.
 * @returns {Map<string, Set<string>>} Allowed command names keyed by GitHub user id.
 */
function loadTrustedCommandUsers({trustedUsersFile = process.env.AUTO_APPROVED_USERS_FILE || AUTO_APPROVED_USERS_FILE} = {}) {
  let trustedUsers

  try {
    const resolvedTrustedUsersFile = resolveTrustedUsersFile(trustedUsersFile)
    trustedUsers = JSON.parse(fs.readFileSync(resolvedTrustedUsersFile, 'utf8'))
  } catch (error) {
    console.log(`trusted command users unavailable: ${error.message}`)
    return new Map()
  }

  if (!Array.isArray(trustedUsers)) {
    return new Map()
  }

  const trustedCommandUsers = new Map()

  for (const user of trustedUsers) {
    if (!user || typeof user !== 'object' || Array.isArray(user)) {
      continue
    }

    const userId = normalizeUserId(user.user_id)
    const commands = normalizeAllowedCommands(user.commands)

    if (userId && commands.size > 0) {
      trustedCommandUsers.set(userId, commands)
    }
  }

  return trustedCommandUsers
}

/**
 * Determine whether a trusted user configuration allows a command.
 *
 * @param {object} options Options for checking the command.
 * @param {Map<string, Set<string>>} options.trustedCommandUsers Trusted user command map.
 * @param {object} options.userId GitHub user id.
 * @param {string} options.command Bot command name.
 * @returns {boolean} Whether the command is allowed.
 */
function trustedUserCanRunCommand({trustedCommandUsers, userId, command}) {
  const commands = trustedCommandUsers.get(normalizeUserId(userId))

  return Boolean(commands && (commands.has(ALL_COMMANDS) || commands.has(normalizeCommandName(command))))
}

/**
 * Determine whether the command commenter is the issue author.
 *
 * @param {object} options Options for checking authorship.
 * @param {string} options.command Bot command name.
 * @param {object} options.commentAuthorId Comment author GitHub user id.
 * @param {object} options.issueAuthorId Issue author GitHub user id.
 * @returns {boolean} Whether the issue author may run the command.
 */
function issueAuthorCanRunCommand({command, commentAuthorId, issueAuthorId}) {
  const normalizedCommentAuthorId = normalizeUserId(commentAuthorId)

  return normalizeCommandName(command) === 'edit' &&
    normalizedCommentAuthorId !== '' &&
    normalizedCommentAuthorId === normalizeUserId(issueAuthorId)
}

/**
 * Get the repository permission level for a GitHub actor.
 *
 * @param {object} options Options for checking repository permission.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string} options.actor GitHub actor login.
 * @returns {Promise<string>} Repository permission level.
 */
async function getRepositoryPermission({github, context, actor}) {
  if (!actor) {
    return ''
  }

  try {
    const response = await github.rest.repos.getCollaboratorPermissionLevel({
      ...repoParams(context),
      username: actor
    })

    return `${response.data.permission}`
  } catch (error) {
    console.log(`repository permission unavailable for ${actor}: ${error.message}`)
    return ''
  }
}

/**
 * Determine whether the comment actor is a repository admin.
 *
 * @param {object} options Options for checking admin permissions.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string} options.actor GitHub actor login.
 * @returns {Promise<boolean>} Whether the actor has admin permission on the repository.
 */
async function actorIsRepositoryAdmin({github, context, actor}) {
  const permission = await getRepositoryPermission({github, context, actor})

  return permission === ADMIN_REPOSITORY_PERMISSION
}

/**
 * Determine whether the command is authorized for this comment.
 *
 * @param {object} options Options for checking authorization.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string} options.command Bot command name.
 * @param {string} options.actor GitHub actor login.
 * @param {object} options.commentAuthorId Comment author GitHub user id.
 * @param {object} options.issueAuthorId Issue author GitHub user id.
 * @param {Map<string, Set<string>>} [options.trustedCommandUsers] Trusted user command map.
 * @returns {Promise<boolean>} Whether the command is authorized.
 */
async function canRunCommand({
  github,
  context,
  command,
  actor,
  commentAuthorId,
  issueAuthorId,
  trustedCommandUsers = loadTrustedCommandUsers()
}) {
  if (trustedUserCanRunCommand({trustedCommandUsers, userId: commentAuthorId, command})) {
    return true
  }

  if (issueAuthorCanRunCommand({command, commentAuthorId, issueAuthorId})) {
    return true
  }

  return actorIsRepositoryAdmin({github, context, actor})
}

/**
 * Get the issue comment author id from the event payload or environment.
 *
 * @param {import('./github-issue.js').GitHubScriptContext} context The actions/github-script context object.
 * @returns {string} GitHub user id.
 */
function getCommentAuthorId(context) {
  return normalizeUserId(context.payload?.comment?.user?.id ?? process.env.COMMENT_AUTHOR_ID)
}

/**
 * Get the issue author id from the event payload or environment.
 *
 * @param {import('./github-issue.js').GitHubScriptContext} context The actions/github-script context object.
 * @returns {string} GitHub user id.
 */
function getIssueAuthorId(context) {
  return normalizeUserId(context.payload?.issue?.user?.id ?? process.env.ISSUE_AUTHOR_ID)
}

/**
 * Get the GitHub actor from the event context or environment.
 *
 * @param {import('./github-issue.js').GitHubScriptContext} context The actions/github-script context object.
 * @returns {string} GitHub actor login.
 */
function getActor(context) {
  return context.actor || context.payload?.comment?.user?.login || process.env.GITHUB_ACTOR || ''
}

/**
 * Update the issue body with a replacement YouTube URL and re-trigger request validation.
 *
 * @param {object} options Options for editing a theme request.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string} options.issueBody Current issue body.
 * @param {RegExp} options.youtubeRegex Regular expression used to find the current YouTube URL.
 * @param {string} options.replacementUrl Replacement YouTube URL.
 * @returns {Promise<void>} Promise resolved after the edit workflow finishes.
 */
async function editThemeRequest({github, context, issueBody, youtubeRegex, replacementUrl}) {
  console.log(`og issue_body: ${issueBody}`)

  youtubeRegex.lastIndex = 0
  const currentUrl = youtubeRegex.exec(issueBody)
  console.log(`current_url: ${currentUrl}`)

  if (currentUrl !== null) {
    const updatedIssueBody = issueBody.replace(currentUrl[0], replacementUrl)
    console.log(`updated issue_body: ${updatedIssueBody}`)

    if (updatedIssueBody !== issueBody) {
      await github.rest.issues.update({
        ...issueParams(context),
        body: updatedIssueBody
      })

      const labels = await github.rest.issues.listLabelsOnIssue(issueParams(context))
      const labelsToRemove = ['approve-theme', 'approve-queue', 'request-theme']

      await removeLabelsByName({
        github,
        context,
        currentLabels: labelNames(labels),
        labelsToRemove
      })

      await delay(10000)

      await github.rest.issues.addLabels({
        ...issueParams(context),
        labels: ['request-theme']
      })
    }
  }
}

/**
 * Re-trigger request validation by re-applying the request label.
 *
 * @param {object} options Options for checking a theme request.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<void>} Promise resolved after the check workflow is triggered.
 */
async function checkThemeRequest({github, context}) {
  const labels = await github.rest.issues.listLabelsOnIssue(issueParams(context))

  await removeLabelsByName({
    github,
    context,
    currentLabels: labelNames(labels),
    labelsToRemove: [REQUEST_THEME_LABEL]
  })

  await delay(10000)

  await github.rest.issues.addLabels({
    ...issueParams(context),
    labels: [REQUEST_THEME_LABEL]
  })
}

/**
 * Add the question label to an issue.
 *
 * @param {object} options Options for adding the label.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<void>} Promise resolved after the label is added.
 */
async function addQuestionLabel({github, context}) {
  await github.rest.issues.addLabels({
    ...issueParams(context),
    labels: [QUESTION_LABEL]
  })
}

/**
 * Add a positive reaction to a handled bot command comment.
 *
 * @param {object} options Options for adding the reaction.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {number} options.commentId Issue comment identifier.
 * @returns {Promise<void>} Promise resolved after the reaction is added.
 */
async function addCommandReaction({github, context, commentId}) {
  await github.rest.reactions.createForIssueComment({
    ...repoParams(context),
    comment_id: commentId,
    content: '+1'
  })
}

/**
 * Execute the issue comment command script.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<void>} Promise resolved after command handling finishes.
 */
async function run({github, context}) {
  const {COMMENT_BODY, ISSUE_BODY} = process.env
  const commentId = Number.parseInt(process.env.COMMENT_ID, 10)
  const youtubeRegex = new RegExp(process.env.YT_REGEX, 'gim')
  const comment = normalizeComment(COMMENT_BODY)

  console.log(`comment: ${comment}`)

  const {command, args} = parseCommandComment(comment)

  if (!command) {
    console.log('the comment is not a bot command, exiting')
    return
  }

  if (!KNOWN_COMMANDS.has(command)) {
    console.log('the bot command is unknown, exiting')
    return
  }

  const commandAllowed = await canRunCommand({
    github,
    context,
    command,
    actor: getActor(context),
    commentAuthorId: getCommentAuthorId(context),
    issueAuthorId: getIssueAuthorId(context)
  })

  if (!commandAllowed) {
    console.log('the bot command is not authorized for this commenter, exiting')
    return
  }

  if (command === 'approve') {
    console.log('approve command running')
    await queueIssueForApproval({github, context})
  } else if (command === 'check') {
    console.log('check command running')
    await checkThemeRequest({github, context})
  } else if (command === 'edit') {
    console.log('edit command running')

    await editThemeRequest({
      github,
      context,
      issueBody: `${ISSUE_BODY}`,
      youtubeRegex,
      replacementUrl: args[2]
    })
  } else {
    console.log('question command running')
    await addQuestionLabel({github, context})
  }

  console.log('command ran, adding reaction')
  await addCommandReaction({github, context, commentId})
}

module.exports = {
  addCommandReaction,
  addQuestionLabel,
  actorIsRepositoryAdmin,
  canRunCommand,
  checkThemeRequest,
  editThemeRequest,
  issueAuthorCanRunCommand,
  loadTrustedCommandUsers,
  normalizeComment,
  normalizeCommandName,
  normalizeUserId,
  parseCommandComment,
  run
}
