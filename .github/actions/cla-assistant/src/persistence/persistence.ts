import { context } from '@actions/github'

import { ReactedCommitterMap } from '../interfaces'
import { GitHub } from '@actions/github/lib/utils'
import { getDefaultOctokitClient, getPATOctokit } from '../octokit'

import * as input from '../shared/getInputs'

export async function getFileContent(): Promise<any> {
  const octokitInstance: InstanceType<typeof GitHub> =
    isRemoteRepoOrOrgConfigured() ? getPATOctokit() : getDefaultOctokitClient()

  const result = await octokitInstance.repos.getContent({
    owner: input.getRemoteOrgName() || context.repo.owner,
    repo: input.getRemoteRepoName() || context.repo.repo,
    path: input.getPathToSignatures(),
    ref: input.getBranch()
  })
  return result
}

export async function createFile(contentBinary): Promise<any> {
  const octokitInstance: InstanceType<typeof GitHub> =
    isRemoteRepoOrOrgConfigured() ? getPATOctokit() : getDefaultOctokitClient()

  return octokitInstance.repos.createOrUpdateFileContents({
    owner: input.getRemoteOrgName() || context.repo.owner,
    repo: input.getRemoteRepoName() || context.repo.repo,
    path: input.getPathToSignatures(),
    message:
      input.getCreateFileCommitMessage() ||
      'Creating file for storing CLA Signatures',
    content: contentBinary,
    branch: input.getBranch()
  })
}

export async function updateFile(
  sha: string,
  claFileContent,
  reactedCommitters: ReactedCommitterMap
): Promise<any> {
  const octokitInstance: InstanceType<typeof GitHub> =
    isRemoteRepoOrOrgConfigured() ? getPATOctokit() : getDefaultOctokitClient()

  const pullRequestNo = context.issue.number
  const owner = context.issue.owner
  const repo = context.issue.repo

  claFileContent?.signedContributors.push(...reactedCommitters.newSigned)
  let contentString = JSON.stringify(claFileContent, null, 2)
  let contentBinary = Buffer.from(contentString).toString('base64')
  await octokitInstance.repos.createOrUpdateFileContents({
    owner: input.getRemoteOrgName() || context.repo.owner,
    repo: input.getRemoteRepoName() || context.repo.repo,
    path: input.getPathToSignatures(),
    sha,
    message: input.getSignedCommitMessage()
      ? input
          .getSignedCommitMessage()
          .replace('$contributorName', context.actor)
          // .replace('$pullRequestNo', pullRequestNo.toString())
          .replace('$owner', owner)
          .replace('$repo', repo)
      : `@${context.actor} has signed the CLA in ${owner}/${repo}#${pullRequestNo}`,
    content: contentBinary,
    branch: input.getBranch()
  })
}

function isRemoteRepoOrOrgConfigured(): boolean {
  let isRemoteRepoOrOrgConfigured = false
  if (input?.getRemoteRepoName() || input.getRemoteOrgName()) {
    isRemoteRepoOrOrgConfigured = true
    return isRemoteRepoOrOrgConfigured
  }
  return isRemoteRepoOrOrgConfigured
}
