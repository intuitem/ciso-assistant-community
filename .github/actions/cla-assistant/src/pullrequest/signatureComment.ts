import { octokit } from '../octokit'
import { context } from '@actions/github'
import { CommitterMap, CommittersDetails, ReactedCommitterMap } from '../interfaces'
import { getUseDcoFlag, getCustomPrSignComment } from '../shared/getInputs'

import * as core from '@actions/core'

export default async function signatureWithPRComment(committerMap: CommitterMap, committers): Promise<ReactedCommitterMap> {

    let repoId = context.payload.repository!.id
    let prResponse = await octokit.issues.listComments({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number
    })
    let listOfPRComments = [] as CommittersDetails[]
    let filteredListOfPRComments = [] as CommittersDetails[]

    prResponse?.data.map((prComment) => {
        listOfPRComments.push({
            name: prComment.user.login,
            id: prComment.user.id,
            comment_id: prComment.id,
            body: prComment.body.trim().toLowerCase(),
            created_at: prComment.created_at,
            repoId: repoId,
            pullRequestNo: context.issue.number
        })
    })
    listOfPRComments.map(comment => {
        if (isCommentSignedByUser(comment.body || "", comment.name)) {
            filteredListOfPRComments.push(comment)
        }
    })
    for (var i = 0; i < filteredListOfPRComments.length; i++) {
        delete filteredListOfPRComments[i].body
    }
    /*
    *checking if the reacted committers are not the signed committers(not in the storage file) and filtering only the unsigned committers
    */
    const newSigned = filteredListOfPRComments.filter(commentedCommitter => committerMap.notSigned!.some(notSignedCommitter => commentedCommitter.id === notSignedCommitter.id))

    /*
    * checking if the commented users are only the contributors who has committed in the same PR (This is needed for the PR Comment and changing the status to success when all the contributors has reacted to the PR)
    */
    const onlyCommitters = committers.filter(committer => filteredListOfPRComments.some(commentedCommitter => committer.id == commentedCommitter.id))
    const commentedCommitterMap: ReactedCommitterMap = {
        newSigned,
        onlyCommitters,
        allSignedFlag: false
    }

    return commentedCommitterMap

}

function isCommentSignedByUser(comment: string, commentAuthor: string): boolean {
    if (commentAuthor === 'github-actions[bot]') {
        return false
    }
    if (getCustomPrSignComment() !== "") {
        return getCustomPrSignComment().toLowerCase() === comment
    }
    // using a `string` true or false purposely as github action input cannot have a boolean value
    switch (getUseDcoFlag()) {
        case 'true':
            return comment.match(/^.*i \s*have \s*read \s*the \s*dco \s*document \s*and \s*i \s*hereby \s*sign \s*the \s*dco.*$/) !== null
        case 'false':
            return comment.match(/^.*i \s*have \s*read \s*the \s*cla \s*document \s*and \s*i \s*hereby \s*sign \s*the \s*cla.*$/) !== null
        default:
            return false
    }
}
