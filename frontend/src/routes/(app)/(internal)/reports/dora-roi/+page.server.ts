import { BASE_API_URL } from '$lib/utils/constants';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (!locals.featureflags?.dora) redirect(302, '/');
	const endpoint = `${BASE_API_URL}/entities/dora_roi_lint/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error loading DORA ROI validation');
	}

	const lintResults = await res.json();

	return {
		lintResults
	};
};
