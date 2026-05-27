/**
 * @file Tests for GitHub workflow helper scripts.
 */

const {
  afterEach,
  beforeEach,
  describe,
  expect,
  jest,
  test
} = require('@jest/globals')

const approvalQueue = require('../src/github-scripts/approval-queue.js')
const commentCommand = require('../src/github-scripts/comment-command.js')
const githubIssue = require('../src/github-scripts/github-issue.js')
const labelNextIssue = require('../src/github-scripts/label-next-issue.js')
const queueEligibleSubmission = require('../src/github-scripts/queue-eligible-submission.js')
const relabelIssue = require('../src/github-scripts/relabel-issue.js')
const updateIssueTitle = require('../src/github-scripts/update-issue-title.js')
const updateLabels = require('../src/github-scripts/update-labels.js')
const workflowRunQueue = require('../src/github-scripts/workflow-run-queue.js')

const context = {
  repo: {
    owner: 'LizardByte',
    repo: 'ThemerrDB'
  },
  issue: {
    number: 7
  }
}

/**
 * Build a GitHub labels response from label names.
 *
 * @param {...string} names Label names.
 * @returns {{data: {name: string}[]}} GitHub label response.
 */
function labels(...names) {
  return {
    data: names.map(name => ({name}))
  }
}

/**
 * Replace setTimeout with an immediate callback executor.
 *
 * @returns {void}
 */
function runTimersImmediately() {
  jest.spyOn(globalThis, 'setTimeout').mockImplementation(callback => {
    callback()
    return 0
  })
}

describe('github issue helpers', () => {
  let originalEnv

  beforeEach(() => {
    originalEnv = {...process.env}
    jest.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    process.env = originalEnv
    jest.restoreAllMocks()
  })

  test('builds repository and issue parameters', () => {
    expect(githubIssue.repoParams(context)).toEqual({
      owner: 'LizardByte',
      repo: 'ThemerrDB'
    })
    expect(githubIssue.issueParams(context, '12')).toEqual({
      owner: 'LizardByte',
      repo: 'ThemerrDB',
      issue_number: 12
    })
    expect(githubIssue.issueParams(context)).toEqual({
      owner: 'LizardByte',
      repo: 'ThemerrDB',
      issue_number: 7
    })
  })

  test('extracts label names and waits with delay', async () => {
    runTimersImmediately()

    await githubIssue.delay(10000)

    expect(githubIssue.labelNames(labels('one', 'two'))).toEqual(['one', 'two'])
    expect(globalThis.setTimeout).toHaveBeenCalledWith(expect.any(Function), 10000)
  })

  test('removes only labels that are present', async () => {
    const removedLabels = []
    const github = {
      rest: {
        issues: {
          removeLabel: jest.fn(async params => removedLabels.push(params.name))
        }
      }
    }

    await githubIssue.removeLabelsByName({
      github,
      context,
      currentLabels: ['approve-theme'],
      labelsToRemove: ['approve-theme', 'missing']
    })

    expect(removedLabels).toEqual(['approve-theme'])
  })
})

describe('approval queue', () => {
  beforeEach(() => {
    jest.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  test('lists open issues by label', async () => {
    const listForRepo = jest.fn()
    const github = {
      paginate: jest.fn(async (method, params) => {
        expect(method).toBe(listForRepo)
        expect(params).toEqual({
          owner: 'LizardByte',
          repo: 'ThemerrDB',
          state: 'open',
          labels: 'approve-theme',
          per_page: 100
        })
        return [{number: 1}]
      }),
      rest: {
        issues: {
          listForRepo
        }
      }
    }

    await expect(approvalQueue.listOpenIssuesWithLabel({
      github,
      context,
      label: 'approve-theme'
    })).resolves.toEqual([{number: 1}])
  })

  test('detects active approval only when another issue is active', async () => {
    const github = {
      paginate: jest.fn()
        .mockResolvedValueOnce([{number: 7}])
        .mockResolvedValueOnce([{number: 8}]),
      rest: {
        issues: {
          listForRepo: jest.fn()
        }
      }
    }

    await expect(approvalQueue.hasActiveApproval({
      github,
      context,
      issueNumber: '7'
    })).resolves.toBe(false)
    await expect(approvalQueue.hasActiveApproval({
      github,
      context,
      issueNumber: 7
    })).resolves.toBe(true)
  })

  test('adds queue and active approval labels when the queue is idle', async () => {
    const addedLabels = []
    const github = {
      paginate: jest.fn(async () => []),
      rest: {
        issues: {
          listForRepo: jest.fn(),
          addLabels: jest.fn(async params => addedLabels.push(params.labels))
        }
      }
    }

    await expect(approvalQueue.queueIssueForApproval({github, context}))
      .resolves.toEqual(['approve-queue', 'approve-theme'])
    expect(addedLabels).toEqual([['approve-queue', 'approve-theme']])
  })

  test('adds only the queue label when another approval is active', async () => {
    const addedLabels = []
    const github = {
      paginate: jest.fn(async () => [{number: 8}]),
      rest: {
        issues: {
          listForRepo: jest.fn(),
          addLabels: jest.fn(async params => addedLabels.push(params.labels))
        }
      }
    }

    await expect(approvalQueue.queueIssueForApproval({github, context}))
      .resolves.toEqual(['approve-queue'])
    expect(addedLabels).toEqual([['approve-queue']])
  })

  test('promotes the next queued issue when one exists', async () => {
    const added = []
    const github = {
      paginate: jest.fn(async () => [{number: 9}]),
      rest: {
        issues: {
          listForRepo: jest.fn(),
          addLabels: jest.fn(async params => added.push(params))
        }
      }
    }

    await expect(approvalQueue.labelNextQueuedIssue({github, context}))
      .resolves.toEqual({number: 9})
    expect(added[0]).toMatchObject({
      issue_number: 9,
      labels: ['approve-theme']
    })
  })

  test('does not promote a queued issue when the queue is empty', async () => {
    const github = {
      paginate: jest.fn(async () => []),
      rest: {
        issues: {
          listForRepo: jest.fn(),
          addLabels: jest.fn()
        }
      }
    }

    await expect(approvalQueue.labelNextQueuedIssue({github, context}))
      .resolves.toBeNull()
    expect(github.rest.issues.addLabels).not.toHaveBeenCalled()
  })
})

describe('workflow run queue', () => {
  let originalEnv

  beforeEach(() => {
    originalEnv = {...process.env}
    jest.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    process.env = originalEnv
    jest.restoreAllMocks()
  })

  test('lists older active workflow runs', async () => {
    const listWorkflowRuns = jest.fn()
    const github = {
      paginate: jest.fn(async (method, params) => {
        expect(method).toBe(listWorkflowRuns)
        expect(params).toEqual({
          owner: 'LizardByte',
          repo: 'ThemerrDB',
          workflow_id: 'auto-update-db.yml',
          per_page: 100
        })
        return [
          {id: 40, status: 'in_progress', display_title: 'approve-theme #5'},
          {id: 41, status: 'completed', display_title: 'approve-theme #6'},
          {id: 42, status: 'queued', display_title: 'request-theme #7'},
          {id: 44, status: 'queued', display_title: 'approve-theme #8'}
        ]
      }),
      rest: {
        actions: {
          listWorkflowRuns
        }
      }
    }

    await expect(workflowRunQueue.listActiveWorkflowRuns({
      github,
      context: {...context, runId: 43},
      workflowId: 'auto-update-db.yml'
    })).resolves.toEqual([
      {id: 40, status: 'in_progress', display_title: 'approve-theme #5'},
      {id: 42, status: 'queued', display_title: 'request-theme #7'}
    ])
  })

  test('finds blocking jobs and treats runs without jobs as pending work', async () => {
    const listWorkflowRuns = jest.fn()
    const listJobsForWorkflowRun = jest.fn()
    const jobsByRunId = new Map([
      [10, [{name: 'update', status: 'in_progress'}]],
      [11, []],
      [12, [{name: 'update', status: 'completed'}]],
      [13, [{name: 'call-jekyll-build', status: 'in_progress'}]]
    ])
    const github = {
      paginate: jest.fn(async (method, params) => {
        if (method === listWorkflowRuns) {
          return [
            {id: 10, name: 'Update', run_number: 1, status: 'in_progress', display_title: 'Daily'},
            {id: 11, name: 'Update', run_number: 2, status: 'queued', display_title: 'Daily'},
            {id: 12, name: 'Update', run_number: 3, status: 'in_progress', display_title: 'Daily'},
            {id: 13, name: 'Update', run_number: 4, status: 'in_progress', display_title: 'Daily'}
          ]
        }

        expect(method).toBe(listJobsForWorkflowRun)
        return jobsByRunId.get(params.run_id)
      }),
      rest: {
        actions: {
          listJobsForWorkflowRun,
          listWorkflowRuns
        }
      }
    }

    await expect(workflowRunQueue.findBlockingWorkflowRuns({
      github,
      context: {...context, runId: 20},
      workflowId: 'update-pages.yml',
      jobName: 'update'
    })).resolves.toEqual([
      {id: 10, name: 'Update', run_number: 1, status: 'in_progress', display_title: 'Daily'},
      {id: 11, name: 'Update', run_number: 2, status: 'queued', display_title: 'Daily'}
    ])
  })

  test('uses marker steps to identify blocking workflow runs', async () => {
    const listWorkflowRuns = jest.fn()
    const listJobsForWorkflowRun = jest.fn()
    const jobsByRunId = new Map([
      [80, [{
        name: 'auto_update_db',
        status: 'in_progress',
        steps: [{name: 'Wait for approved database updates', conclusion: 'success'}]
      }]],
      [81, [{
        name: 'auto_update_db',
        status: 'in_progress',
        steps: [{name: 'Wait for approved database updates', conclusion: 'skipped'}]
      }]],
      [82, [{
        name: 'auto_update_db',
        status: 'in_progress',
        steps: [{name: 'Checkout', conclusion: 'success'}]
      }]]
    ])
    const github = {
      paginate: jest.fn(async (method, params) => {
        if (method === listWorkflowRuns) {
          return [
            {id: 80, name: 'Auto Update DB', run_number: 1, status: 'in_progress'},
            {id: 81, name: 'Auto Update DB', run_number: 2, status: 'in_progress'},
            {id: 82, name: 'Auto Update DB', run_number: 3, status: 'in_progress'}
          ]
        }

        expect(method).toBe(listJobsForWorkflowRun)
        return jobsByRunId.get(params.run_id)
      }),
      rest: {
        actions: {
          listJobsForWorkflowRun,
          listWorkflowRuns
        }
      }
    }

    await expect(workflowRunQueue.findBlockingWorkflowRuns({
      github,
      context: {...context, runId: 90},
      workflowId: 'auto-update-db.yml',
      markerStepName: 'Wait for approved database updates'
    })).resolves.toEqual([
      {id: 80, name: 'Auto Update DB', run_number: 1, status: 'in_progress'},
      {id: 82, name: 'Auto Update DB', run_number: 3, status: 'in_progress'}
    ])
  })

  test('waits until older workflow runs finish', async () => {
    runTimersImmediately()
    const listWorkflowRuns = jest.fn()
    const github = {
      paginate: jest.fn()
        .mockImplementationOnce(async method => {
          expect(method).toBe(listWorkflowRuns)
          return [
            {
              id: 30,
              name: 'Auto Update DB',
              run_number: 9,
              status: 'in_progress',
              display_title: 'approve-theme #9'
            }
          ]
        })
        .mockImplementationOnce(async method => {
          expect(method).toBe(listWorkflowRuns)
          return []
        }),
      rest: {
        actions: {
          listWorkflowRuns
        }
      }
    }

    await expect(workflowRunQueue.waitForWorkflowJobs({
      github,
      context: {...context, runId: 31},
      workflowId: 'auto-update-db.yml',
      intervalMs: 5000
    })).resolves.toEqual([])
    expect(globalThis.setTimeout).toHaveBeenCalledWith(expect.any(Function), 5000)
  })

  test('waits until older named jobs finish', async () => {
    runTimersImmediately()
    const listWorkflowRuns = jest.fn()
    const listJobsForWorkflowRun = jest.fn()
    const github = {
      paginate: jest.fn()
        .mockImplementationOnce(async method => {
          expect(method).toBe(listWorkflowRuns)
          return [
            {
              id: 70,
              name: 'Update',
              run_number: 13,
              status: 'in_progress',
              display_title: 'Daily'
            }
          ]
        })
        .mockImplementationOnce(async method => {
          expect(method).toBe(listJobsForWorkflowRun)
          return [{name: 'update', status: 'queued'}]
        })
        .mockImplementationOnce(async method => {
          expect(method).toBe(listWorkflowRuns)
          return []
        }),
      rest: {
        actions: {
          listJobsForWorkflowRun,
          listWorkflowRuns
        }
      }
    }

    await expect(workflowRunQueue.waitForWorkflowJobs({
      github,
      context: {...context, runId: 71},
      workflowId: 'update-pages.yml',
      jobName: 'update',
      intervalMs: 2500
    })).resolves.toEqual([])
    expect(globalThis.setTimeout).toHaveBeenCalledWith(expect.any(Function), 2500)
  })

  test('waits until older marker step runs finish', async () => {
    runTimersImmediately()
    const listWorkflowRuns = jest.fn()
    const listJobsForWorkflowRun = jest.fn()
    const github = {
      paginate: jest.fn()
        .mockImplementationOnce(async method => {
          expect(method).toBe(listWorkflowRuns)
          return [
            {
              id: 90,
              name: 'Auto Update DB',
              run_number: 14,
              status: 'in_progress',
              display_title: '[MOVIE]: Example'
            }
          ]
        })
        .mockImplementationOnce(async method => {
          expect(method).toBe(listJobsForWorkflowRun)
          return [{
            name: 'auto_update_db',
            status: 'in_progress',
            steps: [{name: 'Wait for approved database updates', conclusion: 'success'}]
          }]
        })
        .mockImplementationOnce(async method => {
          expect(method).toBe(listWorkflowRuns)
          return []
        }),
      rest: {
        actions: {
          listJobsForWorkflowRun,
          listWorkflowRuns
        }
      }
    }

    await expect(workflowRunQueue.waitForWorkflowJobs({
      github,
      context: {...context, runId: 91},
      workflowId: 'auto-update-db.yml',
      markerStepName: 'Wait for approved database updates',
      intervalMs: 1000
    })).resolves.toEqual([])
    expect(globalThis.setTimeout).toHaveBeenCalledWith(expect.any(Function), 1000)
  })

  test('returns immediately when no older workflow runs are blocking', async () => {
    const listWorkflowRuns = jest.fn()
    const github = {
      paginate: jest.fn(async () => [
        {id: 50, name: 'Update', run_number: 10, status: 'completed', display_title: 'Daily'},
        {id: 52, name: 'Update', run_number: 11, status: 'in_progress', display_title: 'Daily'}
      ]),
      rest: {
        actions: {
          listWorkflowRuns
        }
      }
    }

    await expect(workflowRunQueue.waitForWorkflowJobs({
      github,
      context: {...context, runId: 51},
      workflowId: 'update-pages.yml'
    })).resolves.toEqual([])
    expect(github.paginate).toHaveBeenCalledWith(
      listWorkflowRuns,
      expect.objectContaining({workflow_id: 'update-pages.yml'})
    )
  })

  test('times out when older workflow runs keep blocking', async () => {
    jest.spyOn(Date, 'now')
      .mockReturnValueOnce(0)
      .mockReturnValueOnce(60001)
    const github = {
      paginate: jest.fn(async () => [
        {
          id: 60,
          name: 'Auto Update DB',
          run_number: 12,
          status: 'in_progress',
          display_title: 'approve-theme #12'
        }
      ]),
      rest: {
        actions: {
          listWorkflowRuns: jest.fn()
        }
      }
    }

    await expect(workflowRunQueue.waitForWorkflowJobs({
      github,
      context: {...context, runId: 61},
      workflowId: 'auto-update-db.yml',
      timeoutMs: 60000
    })).rejects.toThrow('Timed out waiting for auto-update-db.yml runs')
  })
})

describe('comment command script', () => {
  let originalEnv

  beforeEach(() => {
    originalEnv = {...process.env}
    jest.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    process.env = originalEnv
    jest.restoreAllMocks()
  })

  test('normalizes comment spacing', () => {
    expect(commentCommand.normalizeComment('  @LizardByte-bot   approve  '))
      .toBe('@LizardByte-bot approve')
  })

  test('ignores comments that are not bot commands', async () => {
    process.env.COMMENT_BODY = 'plain comment'
    process.env.COMMENT_ID = '123'
    process.env.ISSUE_BODY = 'https://youtu.be/old'
    process.env.YT_REGEX = String.raw`youtu\.be`
    const github = {
      rest: {
        issues: {
          addLabels: jest.fn()
        },
        reactions: {
          createForIssueComment: jest.fn()
        }
      }
    }

    await commentCommand.run({github, context})

    expect(github.rest.issues.addLabels).not.toHaveBeenCalled()
    expect(github.rest.reactions.createForIssueComment).not.toHaveBeenCalled()
  })

  test('does not react when the bot command is unknown', async () => {
    process.env.COMMENT_BODY = '@LizardByte-bot unknown'
    process.env.COMMENT_ID = '123'
    process.env.ISSUE_BODY = 'https://youtu.be/old'
    process.env.YT_REGEX = String.raw`youtu\.be`
    const github = {
      rest: {
        reactions: {
          createForIssueComment: jest.fn()
        }
      }
    }

    await commentCommand.run({github, context})

    expect(github.rest.reactions.createForIssueComment).not.toHaveBeenCalled()
  })

  test('queues approval commands and reacts to the comment', async () => {
    process.env.COMMENT_BODY = '@LizardByte-bot approve'
    process.env.COMMENT_ID = '123'
    process.env.ISSUE_BODY = 'https://youtu.be/old'
    process.env.YT_REGEX = String.raw`youtu\.be`
    const github = {
      paginate: jest.fn(async () => []),
      rest: {
        issues: {
          listForRepo: jest.fn(),
          addLabels: jest.fn()
        },
        reactions: {
          createForIssueComment: jest.fn()
        }
      }
    }

    await commentCommand.run({github, context})

    expect(github.rest.issues.addLabels).toHaveBeenCalledWith(expect.objectContaining({
      issue_number: 7,
      labels: ['approve-queue', 'approve-theme']
    }))
    expect(github.rest.reactions.createForIssueComment).toHaveBeenCalledWith({
      owner: 'LizardByte',
      repo: 'ThemerrDB',
      comment_id: 123,
      content: '+1'
    })
  })

  test('skips edit updates when no YouTube URL is present', async () => {
    const github = {
      rest: {
        issues: {
          update: jest.fn()
        }
      }
    }

    await commentCommand.editThemeRequest({
      github,
      context,
      issueBody: 'no link',
      youtubeRegex: /youtu\.be/gim,
      replacementUrl: 'https://youtu.be/new'
    })

    expect(github.rest.issues.update).not.toHaveBeenCalled()
  })

  test('skips edit updates when the replacement does not change the body', async () => {
    const github = {
      rest: {
        issues: {
          update: jest.fn()
        }
      }
    }

    await commentCommand.editThemeRequest({
      github,
      context,
      issueBody: 'https://youtu.be/old',
      youtubeRegex: /https:\/\/youtu\.be\/old/gim,
      replacementUrl: 'https://youtu.be/old'
    })

    expect(github.rest.issues.update).not.toHaveBeenCalled()
  })

  test('edits theme requests and re-applies the request label', async () => {
    runTimersImmediately()
    const removedLabels = []
    const github = {
      rest: {
        issues: {
          update: jest.fn(),
          listLabelsOnIssue: jest.fn(async () => labels(
            'approve-theme',
            'approve-queue',
            'request-theme'
          )),
          removeLabel: jest.fn(async params => removedLabels.push(params.name)),
          addLabels: jest.fn()
        }
      }
    }

    await commentCommand.editThemeRequest({
      github,
      context,
      issueBody: 'https://youtu.be/old',
      youtubeRegex: /https:\/\/youtu\.be\/old/gim,
      replacementUrl: 'https://youtu.be/new'
    })

    expect(github.rest.issues.update).toHaveBeenCalledWith(expect.objectContaining({
      issue_number: 7,
      body: 'https://youtu.be/new'
    }))
    expect(removedLabels).toEqual(['approve-theme', 'approve-queue', 'request-theme'])
    expect(github.rest.issues.addLabels).toHaveBeenCalledWith(expect.objectContaining({
      labels: ['request-theme']
    }))
  })

  test('runs edit commands from environment values', async () => {
    runTimersImmediately()
    process.env.COMMENT_BODY = '@LizardByte-bot edit https://youtu.be/new'
    process.env.COMMENT_ID = '123'
    process.env.ISSUE_BODY = 'https://youtu.be/old'
    process.env.YT_REGEX = String.raw`https:\/\/youtu\.be\/old`
    const github = {
      rest: {
        issues: {
          update: jest.fn(),
          listLabelsOnIssue: jest.fn(async () => labels()),
          removeLabel: jest.fn(),
          addLabels: jest.fn()
        },
        reactions: {
          createForIssueComment: jest.fn()
        }
      }
    }

    await commentCommand.run({github, context})

    expect(github.rest.issues.update).toHaveBeenCalledWith(expect.objectContaining({
      body: 'https://youtu.be/new'
    }))
    expect(github.rest.reactions.createForIssueComment).toHaveBeenCalled()
  })
})

describe('relabel issue script', () => {
  beforeEach(() => {
    jest.spyOn(console, 'log').mockImplementation(() => {})
    runTimersImmediately()
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  test('removes transient labels and restores request-theme when present', async () => {
    const removedLabels = []
    const github = {
      rest: {
        issues: {
          listLabelsOnIssue: jest.fn(async () => labels(
            'approve-theme',
            'approve-queue',
            'question',
            'request-theme'
          )),
          removeLabel: jest.fn(async params => removedLabels.push(params.name)),
          addLabels: jest.fn()
        }
      }
    }

    await relabelIssue.run({github, context})

    expect(removedLabels).toEqual([
      'approve-theme',
      'approve-queue',
      'question',
      'request-theme'
    ])
    expect(github.rest.issues.addLabels).toHaveBeenCalledWith(expect.objectContaining({
      labels: ['edited', 'request-theme']
    }))
  })

  test('adds only edited when request-theme was absent', async () => {
    const github = {
      rest: {
        issues: {
          listLabelsOnIssue: jest.fn(async () => labels()),
          removeLabel: jest.fn(),
          addLabels: jest.fn()
        }
      }
    }

    await relabelIssue.run({github, context})

    expect(github.rest.issues.removeLabel).not.toHaveBeenCalled()
    expect(github.rest.issues.addLabels).toHaveBeenCalledWith(expect.objectContaining({
      labels: ['edited']
    }))
  })
})

describe('update labels script', () => {
  let originalEnv

  beforeEach(() => {
    originalEnv = {...process.env}
    jest.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    process.env = originalEnv
    jest.restoreAllMocks()
  })

  test('sets label state in place', () => {
    const currentLabels = ['existing']

    updateLabels.setLabelState(currentLabels, 'new', true)
    updateLabels.setLabelState(currentLabels, 'new', true)
    updateLabels.setLabelState(currentLabels, 'existing', false)
    updateLabels.setLabelState(currentLabels, 'missing', false)

    expect(currentLabels).toEqual(['new'])
  })

  test('adds duplicate and removes queue while continuing approval', async () => {
    process.env.EXCEPTION = 'false'
    process.env.DUPLICATE = 'true'
    const github = {
      rest: {
        issues: {
          listLabelsOnIssue: jest.fn(async () => labels('approve-theme', 'approve-queue')),
          setLabels: jest.fn()
        }
      }
    }

    await expect(updateLabels.run({github, context})).resolves.toBe('true')
    expect(github.rest.issues.setLabels).toHaveBeenCalledWith(expect.objectContaining({
      labels: ['approve-theme', 'duplicate']
    }))
  })

  test('removes resolved duplicate and approval label when an exception exists', async () => {
    process.env.EXCEPTION = 'true'
    process.env.DUPLICATE = 'false'
    const github = {
      rest: {
        issues: {
          listLabelsOnIssue: jest.fn(async () => labels(
            'exception',
            'duplicate',
            'approve-theme',
            'approve-queue'
          )),
          setLabels: jest.fn()
        }
      }
    }

    await expect(updateLabels.run({github, context})).resolves.toBe('true')
    expect(github.rest.issues.setLabels).toHaveBeenCalledWith(expect.objectContaining({
      labels: ['exception']
    }))
  })

  test('returns undefined when approval is not active', async () => {
    process.env.EXCEPTION = 'false'
    process.env.DUPLICATE = 'false'
    const github = {
      rest: {
        issues: {
          listLabelsOnIssue: jest.fn(async () => labels('approve-queue')),
          setLabels: jest.fn()
        }
      }
    }

    await expect(updateLabels.run({github, context})).resolves.toBeUndefined()
    expect(github.rest.issues.setLabels).toHaveBeenCalledWith(expect.objectContaining({
      labels: []
    }))
  })
})

describe('simple github-script entrypoints', () => {
  let originalEnv

  beforeEach(() => {
    originalEnv = {...process.env}
    jest.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    process.env = originalEnv
    jest.restoreAllMocks()
  })

  test('updates the issue title', async () => {
    process.env.ISSUE_TITLE = 'Updated title'
    const github = {
      rest: {
        issues: {
          update: jest.fn()
        }
      }
    }

    await updateIssueTitle.run({github, context})

    expect(github.rest.issues.update).toHaveBeenCalledWith({
      owner: 'LizardByte',
      repo: 'ThemerrDB',
      issue_number: 7,
      title: 'Updated title'
    })
  })

  test('queues an eligible submission', async () => {
    const github = {
      paginate: jest.fn(async () => []),
      rest: {
        issues: {
          listForRepo: jest.fn(),
          addLabels: jest.fn()
        }
      }
    }

    await queueEligibleSubmission.run({github, context})

    expect(github.rest.issues.addLabels).toHaveBeenCalledWith(expect.objectContaining({
      labels: ['approve-queue', 'approve-theme']
    }))
  })

  test('labels the next queued issue', async () => {
    const github = {
      paginate: jest.fn(async () => [{number: 12}]),
      rest: {
        issues: {
          listForRepo: jest.fn(),
          addLabels: jest.fn()
        }
      }
    }

    await labelNextIssue.run({github, context})

    expect(github.rest.issues.addLabels).toHaveBeenCalledWith(expect.objectContaining({
      issue_number: 12,
      labels: ['approve-theme']
    }))
  })
})
