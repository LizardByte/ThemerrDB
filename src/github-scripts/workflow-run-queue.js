/**
 * @file Cross-workflow queue helpers for database update workflows.
 */

const {delay, repoParams} = require('./github-issue.js')

const ACTIVE_JOB_STATUSES = new Set([
  'in_progress',
  'pending',
  'queued',
  'requested',
  'waiting'
])
const BLOCKING_WORKFLOW_STATUSES = new Set(['in_progress'])
const DEFAULT_WAIT_INTERVAL_MS = 30000
const DEFAULT_WAIT_TIMEOUT_MS = 60 * 60 * 1000

/**
 * Determine whether a job status may still perform work.
 *
 * @param {string} status GitHub Actions status.
 * @returns {boolean} Whether the status is active.
 */
function isActiveJobStatus(status) {
  return ACTIVE_JOB_STATUSES.has(status)
}

/**
 * Determine whether a run was created before the current run.
 *
 * @param {object} run GitHub workflow run.
 * @param {number|string} currentRunId Current workflow run id.
 * @returns {boolean} Whether the run is older than the current run.
 */
function isOlderRun(run, currentRunId) {
  return Number(run.id) < Number(currentRunId)
}

/**
 * Determine whether a run matches the requested display title prefix.
 *
 * @param {object} run GitHub workflow run.
 * @param {string} runTitlePrefix Prefix required for the run display title.
 * @returns {boolean} Whether the run title matches.
 */
function matchesRunTitlePrefix(run, runTitlePrefix) {
  return String(run.display_title ?? '').startsWith(runTitlePrefix)
}

/**
 * Determine whether a run was triggered by an ignored event.
 *
 * @param {object} run GitHub workflow run.
 * @param {string[]} ignoredEvents Workflow event names to ignore.
 * @returns {boolean} Whether the run event is ignored.
 */
function hasIgnoredEvent(run, ignoredEvents) {
  return ignoredEvents.includes(run.event)
}

/**
 * List older active runs for a workflow.
 *
 * @param {object} options Options for listing workflow runs.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string} options.workflowId Workflow file name or id.
 * @param {number|string} [options.currentRunId=context.runId] Current workflow run id.
 * @param {string} [options.runTitlePrefix=''] Prefix required for the run display title.
 * @param {string[]} [options.ignoredEvents=[]] Workflow event names to ignore.
 * @returns {Promise<object[]>} Older active matching workflow runs.
 */
async function listActiveWorkflowRuns({
  github,
  context,
  workflowId,
  currentRunId = context.runId,
  ignoredEvents = [],
  runTitlePrefix = ''
}) {
  // Query each blocking status separately so the API returns only currently
  // running workflows, instead of paginating the workflow's entire history.
  const runGroups = await Promise.all(
    [...BLOCKING_WORKFLOW_STATUSES].map(status =>
      github.paginate(github.rest.actions.listWorkflowRuns, {
        ...repoParams(context),
        workflow_id: workflowId,
        status,
        per_page: 100
      })
    )
  )

  return runGroups
    .flat()
    .filter(run =>
      BLOCKING_WORKFLOW_STATUSES.has(run.status) &&
      isOlderRun(run, currentRunId) &&
      !hasIgnoredEvent(run, ignoredEvents) &&
      matchesRunTitlePrefix(run, runTitlePrefix)
    )
}

/**
 * Determine whether a marker step identifies a blocking workflow run.
 *
 * @param {object} job GitHub Actions job.
 * @param {string} markerStepName Step name that marks the blocking path.
 * @returns {boolean|undefined} Whether the marker blocks, or undefined when the marker was not found.
 */
function markerStepBlocks(job, markerStepName) {
  const markerStep = job.steps.find(step => step.name === markerStepName)

  if (markerStep === undefined) {
    return undefined
  }

  return markerStep.conclusion !== 'skipped'
}

/**
 * Determine whether an active workflow run has a blocking job.
 *
 * @param {object} options Options for checking workflow jobs.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {object} options.run GitHub workflow run.
 * @param {string} [options.jobName] Optional job name to match.
 * @param {string} [options.markerStepName] Optional step name that marks the blocking path.
 * @returns {Promise<boolean>} Whether the run should block the current job.
 */
async function runHasBlockingJob({github, context, run, jobName, markerStepName}) {
  if (jobName === undefined && markerStepName === undefined) {
    return true
  }

  const jobs = await github.paginate(github.rest.actions.listJobsForWorkflowRun, {
    ...repoParams(context),
    run_id: run.id,
    per_page: 100
  })

  if (jobs.length === 0) {
    return true
  }

  const matchingJobs = jobName === undefined ? jobs : jobs.filter(job => job.name === jobName)

  if (matchingJobs.length === 0) {
    return false
  }

  if (markerStepName === undefined) {
    return matchingJobs.some(job => isActiveJobStatus(job.status))
  }

  const markerStates = new Set(matchingJobs.map(job => markerStepBlocks(job, markerStepName)))

  if (markerStates.has(true)) {
    return true
  }

  return markerStates.has(undefined)
}

/**
 * Find older runs that should block the current job.
 *
 * @param {object} options Options for finding blocking workflow runs.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string} options.workflowId Workflow file name or id.
 * @param {string} [options.jobName] Optional job name to match.
 * @param {string} [options.markerStepName] Optional step name that marks the blocking path.
 * @param {number|string} [options.currentRunId=context.runId] Current workflow run id.
 * @param {string} [options.runTitlePrefix=''] Prefix required for the run display title.
 * @param {string[]} [options.ignoredEvents=[]] Workflow event names to ignore.
 * @returns {Promise<object[]>} Older blocking workflow runs.
 */
async function findBlockingWorkflowRuns(options) {
  const runs = await listActiveWorkflowRuns(options)
  const blockingRuns = []

  for (const run of runs) {
    if (await runHasBlockingJob({...options, run})) {
      blockingRuns.push(run)
    }
  }

  return blockingRuns
}

/**
 * Build a compact description of workflow runs for logs and errors.
 *
 * @param {object[]} runs GitHub workflow runs.
 * @returns {string} Human-readable run summary.
 */
function describeRuns(runs) {
  return runs
    .map(run => `${run.name} #${run.run_number} (${run.status})`)
    .join(', ')
}

/**
 * Wait until no older conflicting workflow runs are active.
 *
 * @param {object} options Options for waiting on workflow runs.
 * @param {object} options.github Authenticated Octokit client from actions/github-script.
 * @param {import('./github-issue.js').GitHubScriptContext} options.context The actions/github-script context object.
 * @param {string} options.workflowId Workflow file name or id.
 * @param {string} [options.jobName] Optional job name to match.
 * @param {string} [options.markerStepName] Optional step name that marks the blocking path.
 * @param {number} [options.intervalMs=30000] Delay between checks.
 * @param {number} [options.timeoutMs=3600000] Maximum wait time.
 * @param {string} [options.runTitlePrefix=''] Prefix required for the run display title.
 * @param {string[]} [options.ignoredEvents=[]] Workflow event names to ignore.
 * @returns {Promise<object[]>} Empty array when the wait completes.
 */
async function waitForWorkflowJobs(options) {
  const {
    intervalMs = DEFAULT_WAIT_INTERVAL_MS,
    jobName,
    markerStepName,
    timeoutMs = DEFAULT_WAIT_TIMEOUT_MS,
    workflowId
  } = options
  const startedAt = Date.now()

  while (true) {
    const blockingRuns = await findBlockingWorkflowRuns(options)

    if (blockingRuns.length === 0) {
      console.log(`No older ${workflowId} runs are blocking this job`)
      return []
    }

    if (Date.now() - startedAt >= timeoutMs) {
      throw new Error(`Timed out waiting for ${workflowId} runs: ${describeRuns(blockingRuns)}`)
    }

    const jobDescription = markerStepName ?? (jobName === undefined ? 'workflow runs' : `${jobName} jobs`)
    console.log(`Waiting for older ${workflowId} ${jobDescription}: ${describeRuns(blockingRuns)}`)
    await delay(intervalMs)
  }
}

module.exports = {
  findBlockingWorkflowRuns,
  listActiveWorkflowRuns,
  waitForWorkflowJobs
}
