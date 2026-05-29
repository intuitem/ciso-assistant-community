import { octokit } from '../octokit'
import * as core from '@actions/core'
import { context } from '@actions/github'

export async function lockPullRequest() {
    core.info('Locking the Pull Request to safe guard the Pull Request CLA Signatures')
    const pullRequestNo: number = context.issue.number
    try {
        await octokit.issues.lock(
            {
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: pullRequestNo
            }
        )
        core.info(`successfully locked the pull request ${pullRequestNo}`)
    } catch (e) {
        core.error(`failed when locking the pull request `)

    }

}
