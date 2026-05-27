/**
 * @file Relabels edited issues so theme validation can run again.
 */

const {
  delay,
  issueParams,
  labelNames,
  removeLabelsByName
} = require('./github-issue.js')

/**
 * Relabel an edited issue and restore request-theme when it was present.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<void>} Promise resolved after relabeling finishes.
 */
async function run({github, context}) {
  const labels = await github.rest.issues.listLabelsOnIssue(issueParams(context))
  const currentLabels = labelNames(labels)
  const labelsToRemove = ['approve-theme', 'approve-queue', 'question']

  await removeLabelsByName({
    github,
    context,
    currentLabels,
    labelsToRemove
  })

  const requestLabel = 'request-theme'
  const labelRequest = currentLabels.includes(requestLabel)

  if (labelRequest) {
    await github.rest.issues.removeLabel({
      ...issueParams(context),
      name: requestLabel
    })
  }

  await delay(10000)

  const labelsAdd = ['edited']

  if (labelRequest) {
    labelsAdd.push(requestLabel)
  }

  await github.rest.issues.addLabels({
    ...issueParams(context),
    labels: labelsAdd
  })
}

module.exports = {
  run
}
