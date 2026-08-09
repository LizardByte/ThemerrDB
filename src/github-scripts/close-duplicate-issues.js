/**
 * @file Closes duplicate open theme requests while preserving the oldest issue.
 */

const {issueParams, repoParams} = require('./github-issue.js')

const DUPLICATE_LABEL = 'duplicate'
const REQUEST_THEME_LABEL = 'request-theme'
const UNNORMALIZED_TITLE_PREFIX = '[THEME]:'

/**
 * List open theme requests from oldest to newest.
 *
 * @param {object} options Options for listing theme requests.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<object[]>} Open theme request issues.
 */
async function listOpenThemeRequests({github, context}) {
  return await github.paginate(github.rest.issues.listForRepo, {
    ...repoParams(context),
    state: 'open',
    labels: REQUEST_THEME_LABEL,
    sort: 'created',
    direction: 'asc',
    per_page: 100
  })
}

/**
 * Match duplicate issue titles, keeping the first (oldest) issue in each group.
 *
 * Unnormalized issue-form titles are ignored because they are not yet safe to
 * compare. Pull requests are also ignored if one happens to carry the request
 * label.
 *
 * @param {object[]} issues Open issues ordered from oldest to newest.
 * @returns {{canonical: object, duplicate: object}[]} Duplicate closure plan.
 */
function planDuplicateClosures(issues) {
  const canonicalByTitle = new Map()
  const closures = []

  for (const issue of issues) {
    if (issue.pull_request !== undefined || issue.title.startsWith(UNNORMALIZED_TITLE_PREFIX)) {
      continue
    }

    const canonical = canonicalByTitle.get(issue.title)
    if (canonical === undefined) {
      canonicalByTitle.set(issue.title, issue)
      continue
    }

    closures.push({canonical, duplicate: issue})
  }

  return closures
}

/**
 * Build the comment that directs discussion and reactions to the older issue.
 *
 * @param {object} canonical Oldest matching issue.
 * @returns {string} Duplicate closure comment.
 */
function duplicateComment(canonical) {
  const issueLink = `[#${canonical.number}](${canonical.html_url})`
  return `This theme request duplicates ${issueLink}, so it is being closed as not planned.\n\n` +
    'Please leave any feedback on that issue and/or add a 👍 reaction to it to express your interest.'
}

/**
 * Label, comment on, and close one duplicate issue.
 *
 * @param {object} options Options for closing the duplicate.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {object} options.canonical Oldest matching issue.
 * @param {object} options.duplicate Newer matching issue to close.
 * @returns {Promise<void>} Promise resolved after the issue is closed.
 */
async function closeDuplicate({github, context, canonical, duplicate}) {
  const params = issueParams(context, duplicate.number)

  await github.rest.issues.addLabels({
    ...params,
    labels: [DUPLICATE_LABEL]
  })
  await github.rest.issues.createComment({
    ...params,
    body: duplicateComment(canonical)
  })
  await github.rest.issues.update({
    ...params,
    state: 'closed',
    state_reason: 'not_planned'
  })
}

/**
 * Close the current issue when it duplicates an older open theme request.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<string>} "true" when the current issue was closed, otherwise "false".
 */
async function run({github, context}) {
  const issues = await listOpenThemeRequests({github, context})
  const closures = planDuplicateClosures(issues)
  const currentIssueNumber = Number(context.issue.number)
  const closure = closures.find(item => Number(item.duplicate.number) === currentIssueNumber)

  if (closure === undefined) {
    return 'false'
  }

  await closeDuplicate({github, context, ...closure})
  return 'true'
}

/**
 * Close every newer issue in every duplicate group of open theme requests.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<number>} Number of duplicate issues closed.
 */
async function closeExistingDuplicates({github, context}) {
  const issues = await listOpenThemeRequests({github, context})
  const closures = planDuplicateClosures(issues)

  for (const closure of closures) {
    await closeDuplicate({github, context, ...closure})
  }

  return closures.length
}

module.exports = {
  closeExistingDuplicates,
  run
}
