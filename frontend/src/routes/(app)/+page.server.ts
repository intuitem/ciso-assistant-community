import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { CI_TEST } from '$lib/utils/env_constants';

const redirectURL = CI_TEST ? '/analytics' : '/analytics?refresh=1';

export const load: PageServerLoad = async () => {
	redirect(301, redirectURL);
};
