import { octokit } from './octokit'
import { context } from '@actions/github'
import { CommittersDetails } from './interfaces'



export default async function getCommitters(): Promise<CommittersDetails[]> {
    try {
        const committers: CommittersDetails[] = []
        const query = `
        query($owner:String! $name:String! $number:Int! $cursor:String!){
            repository(owner: $owner, name: $name) {
            pullRequest(number: $number) {
                commits(first: 100, after: $cursor) {
                    totalCount
                    edges {
                        node {
                            commit {
                                author {
                                    email
                                    name
                                    user {
                                        id
                                        databaseId
                                        login
                                    }
                                }
                                committer {
                                    name
                                    user {
                                        id
                                        databaseId
                                        login
                                    }
                                }
                            }
                        }
                        cursor
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        }
    }`.replace(/ /g, '')

        let cursor = ''
        let hasNextPage = true
        // Paginate through every page of commits; without this only the first
        // 100 commits are inspected and committers beyond them can slip the CLA.
        while (hasNextPage) {
            const response: any = await octokit.graphql(query, {
                owner: context.repo.owner,
                name: context.repo.repo,
                number: context.issue.number,
                cursor
            })
            const commits = response.repository.pullRequest.commits
            commits.edges.forEach(edge => {
                const committer = extractUserFromCommit(edge.node.commit)
                let user = {
                    name: committer.login || committer.name,
                    id: committer.databaseId || '',
                    pullRequestNo: context.issue.number
                }
                if (committers.map((c) => {
                    return c.name
                }).indexOf(user.name) < 0) {
                    committers.push(user)
                }
            })
            hasNextPage = commits.pageInfo.hasNextPage
            cursor = commits.pageInfo.endCursor
        }

        return committers.filter((committer) => {
            return committer.id !== 41898282
        })

    } catch (e) {
        throw new Error(`graphql call to get the committers details failed: ${e}`)
    }

}
const extractUserFromCommit = (commit) => commit.author.user || commit.committer.user || commit.author || commit.committer
