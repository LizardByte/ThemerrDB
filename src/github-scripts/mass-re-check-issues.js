/**
 * @file Re-triggers validation for open theme requests that are not in approval.
 */

const {
  APPROVE_QUEUE_LABEL,
  APPROVE_THEME_LABEL
} = require('./approval-queue.js')
const {delay, issueParams, repoParams} = require('./github-issue.js')

const APPROVAL_LABELS = new Set([APPROVE_QUEUE_LABEL, APPROVE_THEME_LABEL])
const REQUEST_THEME_LABEL = 'request-theme'
const RECHECK_DELAY_MS = 10000

/**
 * Get a label name from an issue API response.
 *
 * @param {string|{name: string}} label Issue label.
 * @returns {string} Label name.
 */
function issueLabelName(label) {
  if (typeof label === 'string') {
    return label
  }

  return label.name
}

/**
 * Determine whether a theme request is queued or active in the approval flow.
 *
 * @param {object} issue Issue API response.
 * @returns {boolean} Whether the issue is in approval.
 */
function isIssueInApproval(issue) {
  return issue.labels.some(label => APPROVAL_LABELS.has(issueLabelName(label)))
}

/**
 * Re-apply the request label to every eligible open theme request.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<number>} Number of theme requests re-triggered.
 */
async function recheckThemeRequests({github, context}) {
  const issues = await github.paginate(github.rest.issues.listForRepo, {
    ...repoParams(context),
    state: 'open',
    labels: REQUEST_THEME_LABEL,
    per_page: 100
  })
  const issuesToRecheck = issues.filter(issue => !issue.pull_request && !isIssueInApproval(issue))

  for (const issue of issuesToRecheck) {
    await github.rest.issues.removeLabel({
      ...issueParams(context, issue.number),
      name: REQUEST_THEME_LABEL
    })
  }

  if (issuesToRecheck.length === 0) {
    return 0
  }

  await delay(RECHECK_DELAY_MS)

  for (const issue of issuesToRecheck) {
    await github.rest.issues.addLabels({
      ...issueParams(context, issue.number),
      labels: [REQUEST_THEME_LABEL]
    })
  }

  return issuesToRecheck.length
}

module.exports = {
  isIssueInApproval,
  issueLabelName,
  recheckThemeRequests
}
