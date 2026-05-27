/**
 * @file Updates the current issue title from the generated title artifact.
 */

const {issueParams} = require('./github-issue.js')

/**
 * Update the current issue title from the ISSUE_TITLE environment variable.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<void>} Promise resolved after the title update finishes.
 */
async function run({github, context}) {
  await github.rest.issues.update({
    ...issueParams(context),
    title: process.env.ISSUE_TITLE
  })
}

module.exports = {
  run
}
