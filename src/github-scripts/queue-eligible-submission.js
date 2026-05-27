/**
 * @file actions/github-script entrypoint for queueing an eligible submission.
 */

const {queueIssueForApproval} = require('./approval-queue.js')

/**
 * Queue the current issue for approval.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<void>} Promise resolved after the issue is queued.
 */
async function run({github, context}) {
  await queueIssueForApproval({github, context})
}

module.exports = {
  run
}
