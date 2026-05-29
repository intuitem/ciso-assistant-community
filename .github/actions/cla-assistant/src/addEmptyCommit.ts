import { octokit } from './octokit'
import { context } from '@actions/github'

import * as core from '@actions/core'
import * as input from './shared/getInputs'
import { getPrSignComment } from './shared/pr-sign-comment'


export async function addEmptyCommit() {
    const contributorName: string = context?.payload?.comment?.user?.login
    core.info(`Adding empty commit for ${contributorName} who has signed the CLA `)

    if (context.payload.comment) {

        //Do empty commit only when the contributor signs the CLA with the PR comment
        if (context.payload.comment.body.toLowerCase().trim() === getPrSignComment().toLowerCase().trim()) {
            try {
                const message = input.getSignedCommitMessage() ?
                    input.getSignedCommitMessage().replace('$contributorName', contributorName) :
                    ` @${contributorName} has signed the CLA `
                const pullRequestResponse = await octokit.pulls.get({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    pull_number: context.payload.issue!.number
                })

                const baseCommit = await octokit.git.getCommit({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    commit_sha: pullRequestResponse.data.head.sha
                })

                const tree = await octokit.git.getTree({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    tree_sha: baseCommit.data.tree.sha
                })
                const newCommit = await octokit.git.createCommit(
                    {
                        owner: context.repo.owner,
                        repo: context.repo.repo,
                        message: message,
                        tree: tree.data.sha,
                        parents: [pullRequestResponse.data.head.sha]
                    }
                )
                return octokit.git.updateRef({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    ref: `heads/${pullRequestResponse.data.head.ref}`,
                    sha: newCommit.data.sha
                })

            } catch (error) {
                core.error(`failed when adding empty commit  with the contributor's signature name: ${error} `)

            }
        }
    }
    return
}
