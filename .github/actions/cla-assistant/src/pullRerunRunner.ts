import { context } from '@actions/github'
import { octokit } from './octokit'

import * as core from '@actions/core'

// Note: why this  re-run of the last failed CLA workflow status check is explained this issue https://github.com/cla-assistant/github-action/issues/39
export async function reRunLastWorkFlowIfRequired() {
  if (context.eventName === 'pull_request') {
    core.debug(`rerun not required for event - pull_request`)
    return
  }

  const branch = await getBranchOfPullRequest()
  const workflowId = await getSelfWorkflowId()
  const runs = await listWorkflowRunsInBranch(branch, workflowId)

  if (runs.data.total_count > 0) {
    const run = runs.data.workflow_runs[0].id

    const isLastWorkFlowFailed: boolean = await checkIfLastWorkFlowFailed(run)
    if (isLastWorkFlowFailed) {
      core.debug(`Rerunning build run ${run}`)
      await reRunWorkflow(run).catch(error =>
        core.error(`Error occurred when re-running the workflow: ${error}`)
      )
    }
  }
}

async function getBranchOfPullRequest(): Promise<string> {
  const pullRequest = await octokit.pulls.get({
    owner: context.repo.owner,
    repo: context.repo.repo,
    pull_number: context.issue.number
  })

  return pullRequest.data.head.ref
}

async function getSelfWorkflowId(): Promise<number> {
  const perPage = 30
  let hasNextPage = true

  for (let page = 1; hasNextPage === true; page++) {
    const workflowList = await octokit.actions.listRepoWorkflows({
      owner: context.repo.owner,
      repo: context.repo.repo,
      per_page: perPage,
      page
    })

    if (workflowList.data.total_count < page * perPage) {
      hasNextPage = false
    }

    const workflow = workflowList.data.workflows.find(
      w => w.name == context.workflow
    )

    if (workflow) {
      return workflow.id
    }
  }

  throw new Error(
    `Unable to locate this workflow's ID in this repository, can't trigger job..`
  )
}

async function listWorkflowRunsInBranch(
  branch: string,
  workflowId: number
): Promise<any> {
  console.debug(branch)
  const runs = await octokit.actions.listWorkflowRuns({
    owner: context.repo.owner,
    repo: context.repo.repo,
    branch,
    workflow_id: workflowId,
    event: 'pull_request_target'
  })
  return runs
}

async function reRunWorkflow(run: number): Promise<any> {
  // Personal Access token with repo scope is required to access this api - https://github.community/t/bug-rerun-workflow-api-not-working/126742
  await octokit.actions.reRunWorkflow({
    owner: context.repo.owner,
    repo: context.repo.repo,
    run_id: run
  })
}

async function checkIfLastWorkFlowFailed(run: number): Promise<boolean> {
  const response: any = await octokit.actions.getWorkflowRun({
    owner: context.repo.owner,
    repo: context.repo.repo,
    run_id: run
  })

  return response.data.conclusion == 'failure'
}
