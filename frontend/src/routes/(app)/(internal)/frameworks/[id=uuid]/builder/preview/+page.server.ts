import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/frameworks/${params.id}/object/`);
	const frameworkData = await res.json();

	return {
		framework: frameworkData,
		title: `Preview - ${frameworkData.name}`
	};
}) satisfies PageServerLoad;
