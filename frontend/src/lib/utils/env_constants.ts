import * as env from '$env/static/private';

// This file is separate from constant.ts because '$env/static/private' can only be imported on the server-side.

export const CI_TEST: boolean = Object.hasOwn(env, 'CI_TEST');
