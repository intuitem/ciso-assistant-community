import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	if (!(await locals.getFeatureFlags())?.document_management) redirect(302, '/');
	return {};
};
