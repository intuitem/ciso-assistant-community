import { CommittersDetails } from './interfaces'

import * as input from './shared/getInputs'

function escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function isUserNotInAllowList(committer) {

    const allowListPatterns: string[] = input.getAllowListItem().split(',')

    return allowListPatterns.filter(function (pattern) {
        pattern = pattern.trim()
        if (pattern.includes('*')) {
            const regex = escapeRegExp(pattern).split('\\*').join('.*')

            return new RegExp(regex).test(committer)
        }
        return pattern === committer
    }).length > 0
}

export function checkAllowList(committers: CommittersDetails[]): CommittersDetails[] {
    const committersAfterAllowListCheck: CommittersDetails[] = committers.filter(committer => committer && !(isUserNotInAllowList !== undefined && isUserNotInAllowList(committer.name)))
    return committersAfterAllowListCheck
}
