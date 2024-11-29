import * as env from '$env/static/private';

export const CI_TEST: boolean = Object.hasOwn(env, 'CI_TEST');
