/**
 * @file actions/github-script entrypoint for promoting the next queued issue.
 */

const {labelNextQueuedIssue} = require('./approval-queue.js')

/**
 * Execute queue promotion for the next queued issue.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<void>} Promise resolved after queue promotion completes.
 */
async function run({github, context}) {
  await labelNextQueuedIssue({github, context})
}

module.exports = {
  run
}
