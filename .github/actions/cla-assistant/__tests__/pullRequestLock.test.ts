import * as core from '@actions/core'
import * as github from '@actions/github'
import { context } from '@actions/github'
import { getclas } from '../src/checkcla'
import { lockPullRequest } from '../src/pullRequestLock'
import { run } from '../src/main'
import { mocked } from 'ts-jest/utils'

jest.mock('@actions/core')
jest.mock('@actions/github')

//const mockedLockPullRequest = mocked(lockPullRequest)
