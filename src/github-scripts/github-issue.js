/**
 * @file Shared helpers for GitHub issue scripts executed by actions/github-script.
 */

/**
 * @typedef {object} GitHubScriptContext
 * @property {{owner: string, repo: string}} repo Repository owner and name.
 * @property {{number: number|string}} issue Issue payload metadata.
 */

/**
 * @typedef {object} Label
 * @property {string} name GitHub label name.
 */

/**
 * @typedef {object} LabelResponse
 * @property {Label[]} data GitHub label response data.
 */

/**
 * Build repository parameters for GitHub REST API calls.
 *
 * @param {GitHubScriptContext} context The actions/github-script context object.
 * @returns {{owner: string, repo: string}} Repository parameters.
 */
function repoParams(context) {
  return {
    owner: context.repo.owner,
    repo: context.repo.repo
  }
}

/**
 * Build issue parameters for GitHub REST API calls.
 *
 * @param {GitHubScriptContext} context The actions/github-script context object.
 * @param {number|string} [issueNumber=context.issue.number] Issue number override.
 * @returns {{owner: string, repo: string, issue_number: number}} Issue parameters.
 */
function issueParams(context, issueNumber = context.issue.number) {
  return {
    ...repoParams(context),
    issue_number: Number(issueNumber)
  }
}

/**
 * Resolve after the requested number of milliseconds.
 *
 * @param {number} ms Milliseconds to wait.
 * @returns {Promise<void>} Promise resolved after the delay.
 */
async function delay(ms) {
  await new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Extract label names from a GitHub label response.
 *
 * @param {LabelResponse} labels GitHub label response.
 * @returns {string[]} Label names.
 */
function labelNames(labels) {
  return labels.data.map(label => label.name)
}

/**
 * Remove selected labels that are currently present on the issue.
 *
 * @param {object} options Options for removing labels.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string[]} options.currentLabels Labels currently present on the issue.
 * @param {string[]} options.labelsToRemove Labels to remove when present.
 * @returns {Promise<void>} Promise resolved after removals finish.
 */
async function removeLabelsByName({github, context, currentLabels, labelsToRemove}) {
  for (const labelName of labelsToRemove) {
    if (currentLabels.includes(labelName)) {
      await github.rest.issues.removeLabel({
        ...issueParams(context),
        name: labelName
      })
    }
  }
}

module.exports = {
  delay,
  issueParams,
  labelNames,
  removeLabelsByName,
  repoParams
}
