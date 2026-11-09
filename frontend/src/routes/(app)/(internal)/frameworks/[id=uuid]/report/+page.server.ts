import { BASE_API_URL } from '#lib/utils/constants.js';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { m } from '#paraglide/messages.js';

export const load = (async ({ fetch, params, url }) => {
	const ig = url.searchParams.get('implementation_group');
	const campaign = url.searchParams.get('campaign');
	const reportUrl = new URL(`${BASE_API_URL}/frameworks/${params.id}/report/`);
	if (ig) reportUrl.searchParams.set('implementation_group', ig);
	if (campaign) reportUrl.searchParams.set('campaign', campaign);

	// Stream the report so the page shell can render immediately with a
	// spinner; the body fills in once the API responds. For large frameworks
	// this avoids a multi-second blank screen.
	const reportPromise = fetch(reportUrl.toString()).then(async (res) => {
		if (!res.ok) {
			throw error(res.status, `Failed to load framework report (${res.status})`);
		}
		return res.json();
	});

	const frameworkName = await fetch(`${BASE_API_URL}/frameworks/${params.id}/`)
		.then((res) => (res.ok ? res.json() : null))
		.then((fw) => fw?.name as string | undefined)
		.catch(() => undefined);
	const title = frameworkName ? `${frameworkName} · ${m.frameworkReport()}` : m.frameworkReport();

	return { title, stream: { report: reportPromise } };
}) satisfies PageServerLoad;
