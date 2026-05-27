/**
 * @file Updates issue labels after parsing and validating a theme request.
 */

const {
  APPROVE_QUEUE_LABEL,
  APPROVE_THEME_LABEL
} = require('./approval-queue.js')
const {issueParams, labelNames} = require('./github-issue.js')

/**
 * Add or remove a label name from an in-memory label list.
 *
 * @param {string[]} currentLabels Mutable list of current label names.
 * @param {string} labelName Label name to add or remove.
 * @param {boolean} enabled Whether the label should be present.
 * @returns {void}
 */
function setLabelState(currentLabels, labelName, enabled) {
  const labelExists = currentLabels.includes(labelName)

  if (!labelExists && enabled) {
    currentLabels.push(labelName)
  } else if (labelExists && !enabled) {
    const index = currentLabels.indexOf(labelName)
    currentLabels.splice(index, 1)
  }
}

/**
 * Update labels after issue validation and return whether approval should continue.
 *
 * @param {object} options Options supplied by actions/github-script.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @returns {Promise<string|undefined>} "true" when the approval workflow should continue.
 */
async function run({github, context}) {
  const labels = await github.rest.issues.listLabelsOnIssue(issueParams(context))
  const exception = process.env.EXCEPTION
  const duplicate = process.env.DUPLICATE

  const currentLabels = labelNames(labels)

  setLabelState(currentLabels, 'exception', exception === 'true')
  setLabelState(currentLabels, 'duplicate', duplicate === 'true')

  const labelAdd = currentLabels.includes(APPROVE_THEME_LABEL)

  if (labelAdd && exception === 'true') {
    setLabelState(currentLabels, APPROVE_THEME_LABEL, false)
  }

  setLabelState(currentLabels, APPROVE_QUEUE_LABEL, false)

  await github.rest.issues.setLabels({
    ...issueParams(context),
    labels: currentLabels
  })

  if (labelAdd) {
    return 'true'
  }
}

module.exports = {
  run,
  setLabelState
}
