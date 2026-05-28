/**
 * @file Approval queue helpers for ThemerrDB issue automation workflows.
 */

const {issueParams, repoParams} = require('./github-issue.js')

const APPROVE_QUEUE_LABEL = 'approve-queue'
const APPROVE_THEME_LABEL = 'approve-theme'

/**
 * List open issues that have the requested label.
 *
 * @param {object} options Options for listing issues.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string} options.label Label to filter by.
 * @returns {Promise<object[]>} Open issues that match the label.
 */
async function listOpenIssuesWithLabel({github, context, label}) {
  return github.paginate(github.rest.issues.listForRepo, {
    ...repoParams(context),
    state: 'open',
    labels: label,
    per_page: 100
  })
}

/**
 * Determine whether another issue is already being approved.
 *
 * @param {object} options Options for checking approval state.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {number|string} options.issueNumber Issue number that should not block itself.
 * @returns {Promise<boolean>} Whether another issue already has the approval label.
 */
async function hasActiveApproval({github, context, issueNumber}) {
  const currentIssueNumber = Number(issueNumber)
  const runningIssues = await listOpenIssuesWithLabel({
    github,
    context,
    label: APPROVE_THEME_LABEL
  })

  return runningIssues.some(issue => issue.number !== currentIssueNumber)
}

/**
 * Queue an issue for approval and start it immediately when the queue is idle.
 *
 * @param {object} options Options for queueing an issue.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {number|string} [options.issueNumber=context.issue.number] Issue number to queue.
 * @returns {Promise<string[]>} Labels added to the issue.
 */
async function queueIssueForApproval({github, context, issueNumber = context.issue.number}) {
  const labelsToAdd = [APPROVE_QUEUE_LABEL]
  const activeApproval = await hasActiveApproval({github, context, issueNumber})

  if (activeApproval) {
    console.log(`other issues have ${APPROVE_THEME_LABEL} label, not adding label`)
  } else {
    console.log(`no other issues have ${APPROVE_THEME_LABEL} label, adding label`)
    labelsToAdd.push(APPROVE_THEME_LABEL)
  }

  console.log(`Adding labels: ${labelsToAdd}`)
  await github.rest.issues.addLabels({
    ...issueParams(context, issueNumber),
    labels: labelsToAdd
  })

  return labelsToAdd
}

/**
 * Promote the first queued issue into the active approval slot.
 *
 * @param {object} options Options for queue promotion.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<object|null>} The issue promoted, or null when the queue is empty.
 */
async function labelNextQueuedIssue({github, context}) {
  const currentIssueNumber = Number(context.issue.number)
  const issues = (await listOpenIssuesWithLabel({
    github,
    context,
    label: APPROVE_QUEUE_LABEL
  })).filter(issue => Number(issue.number) !== currentIssueNumber)

  if (issues.length === 0) {
    console.log(`no open issues have ${APPROVE_QUEUE_LABEL} label`)
    return null
  }

  const nextIssue = issues[0]
  console.log(`adding ${APPROVE_THEME_LABEL} label to issue #${nextIssue.number}`)
  await github.rest.issues.addLabels({
    ...issueParams(context, nextIssue.number),
    labels: [APPROVE_THEME_LABEL]
  })

  return nextIssue
}

module.exports = {
  APPROVE_QUEUE_LABEL,
  APPROVE_THEME_LABEL,
  hasActiveApproval,
  labelNextQueuedIssue,
  listOpenIssuesWithLabel,
  queueIssueForApproval
}
