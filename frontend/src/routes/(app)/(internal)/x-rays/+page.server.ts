import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

const getQualityCheckData = async (fetch: any) => {
	try {
		const endpoint = `${BASE_API_URL}/perimeters/quality_check/`;
		const res = await fetch(endpoint);
		const json = await res.json();
		return json.results;
	} catch (error) {
		console.error('Failed to fetch quality check data:', error);
		return null;
	}
};

export const load = (async ({ fetch }) => {
	return {
		title: m.xRays(),
		stream: {
			data: getQualityCheckData(fetch)
		}
	};
}) satisfies PageServerLoad;
