import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params, url }) => {
	const ig = url.searchParams.get('implementation_group');
	const reportUrl = new URL(`${BASE_API_URL}/frameworks/${params.id}/report/`);
	if (ig) reportUrl.searchParams.set('implementation_group', ig);

	const res = await fetch(reportUrl.toString());
	if (!res.ok) {
		throw error(res.status, `Failed to load framework report (${res.status})`);
	}
	const report = await res.json();

	return { report };
}) satisfies PageServerLoad;
