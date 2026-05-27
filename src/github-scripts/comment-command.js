/**
 * @file Handles issue comment commands for ThemerrDB moderation workflows.
 */

const {queueIssueForApproval} = require('./approval-queue.js')
const {
  delay,
  issueParams,
  labelNames,
  removeLabelsByName,
  repoParams
} = require('./github-issue.js')

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

  if (!comment.startsWith('@LizardByte-bot')) {
    console.log('the comment is not a @LizardByte-bot command, exiting')
    return
  }

  const args = comment.split(' ')
  let commandRan = false

  if (args[1] === 'approve') {
    console.log('approve command running')
    await queueIssueForApproval({github, context})

    commandRan = true
  }

  if (args[1] === 'edit') {
    console.log('edit command running')

    await editThemeRequest({
      github,
      context,
      issueBody: `${ISSUE_BODY}`,
      youtubeRegex,
      replacementUrl: args[2]
    })

    commandRan = true
  }

  if (commandRan) {
    console.log('command ran, adding reaction')
    await addCommandReaction({github, context, commentId})
  }
}

module.exports = {
  addCommandReaction,
  editThemeRequest,
  normalizeComment,
  run
}
