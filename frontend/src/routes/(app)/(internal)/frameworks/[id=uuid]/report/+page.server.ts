import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params, url }) => {
	const ig = url.searchParams.get('implementation_group');
	const reportUrl = new URL(`${BASE_API_URL}/frameworks/${params.id}/report/`);
	if (ig) reportUrl.searchParams.set('implementation_group', ig);

	// Stream the report so the page shell can render immediately with a
	// spinner; the body fills in once the API responds. For large frameworks
	// this avoids a multi-second blank screen.
	const reportPromise = fetch(reportUrl.toString()).then(async (res) => {
		if (!res.ok) {
			throw error(res.status, `Failed to load framework report (${res.status})`);
		}
		return res.json();
	});

	return { stream: { report: reportPromise } };
}) satisfies PageServerLoad;
