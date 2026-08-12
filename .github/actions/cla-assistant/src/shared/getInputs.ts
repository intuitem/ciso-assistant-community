import * as core from '@actions/core'

export const getRemoteRepoName = (): string => {
  return core.getInput('remote-repository-name', { required: false })
}

export const getRemoteOrgName = (): string => {
  return core.getInput('remote-organization-name', { required: false })
}

export const getPathToSignatures = (): string =>
  core.getInput('path-to-signatures', { required: false })

export const getPathToDocument = (): string =>
  core.getInput('path-to-document', { required: false })

export const getBranch = (): string =>
  core.getInput('branch', { required: false })

export const getAllowListItem = (): string =>
  core.getInput('allowlist', { required: false })

export const getEmptyCommitFlag = (): string =>
  core.getInput('empty-commit-flag', { required: false })

export const getSignedCommitMessage = (): string =>
  core.getInput('signed-commit-message', { required: false })

export const getCreateFileCommitMessage = (): string =>
  core.getInput('create-file-commit-message', { required: false })

export const getCustomNotSignedPrComment = (): string =>
  core.getInput('custom-notsigned-prcomment', { required: false })

export const getCustomAllSignedPrComment = (): string =>
  core.getInput('custom-allsigned-prcomment', { required: false })

export const getUseDcoFlag = (): string =>
  core.getInput('use-dco-flag', { required: false })

export const getCustomPrSignComment = (): string =>
  core.getInput('custom-pr-sign-comment', { required: false })

export const lockPullRequestAfterMerge = (): string =>
  core.getInput('lock-pullrequest-aftermerge', { required: false })

export const suggestRecheck = (): string =>
  core.getInput('suggest-recheck', { required: false })
