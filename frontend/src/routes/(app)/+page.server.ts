import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { CI_TEST } from '$lib/utils/env_constants';

const redirectURL = CI_TEST ? '/analytics' : '/analytics?refresh=1';
console.log(`[CI_TEST_VALUE:1] ${CI_TEST}`);

export const load: PageServerLoad = async () => {
	console.log(`[CI_TEST_VALUE:2] ${CI_TEST}`);
	redirect(301, redirectURL);
};
