import { getOctokit } from '@actions/github'

import * as core from '@actions/core'

const githubActionsDefaultToken = process.env.GITHUB_TOKEN
const personalAccessToken = process.env.PERSONAL_ACCESS_TOKEN as string

export const octokit = getOctokit(githubActionsDefaultToken as string)

export function getDefaultOctokitClient() {
  return getOctokit(githubActionsDefaultToken as string)
}
export function getPATOctokit() {
  if (!isPersonalAccessTokenPresent()) {
    core.setFailed(
      `Please add a personal access token as an environment variable for writing signatures in a remote repository/organization as mentioned in the README.md file`
    )
  }
  return getOctokit(personalAccessToken)
}

export function isPersonalAccessTokenPresent(): boolean {
  return personalAccessToken !== undefined && personalAccessToken !== ''
}
