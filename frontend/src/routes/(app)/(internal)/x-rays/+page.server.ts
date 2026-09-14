import { error, type NumericRange } from '@sveltejs/kit';
import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

const getQualityCheckData = async (fetch: any) => {
	const endpoint = `${BASE_API_URL}/folders/quality_check/`;
	const res = await fetch(endpoint);
	if (!res.ok) {
		console.error('Failed to fetch quality check data:', res.status, res.statusText);
		// `error()` and not `throw new Error()`: a streamed rejection goes through
		// `handleError`, which replaces a plain error's message with SvelteKit's
		// generic one. Only an HttpError body reaches the page as written.
		error(res.status as NumericRange<400, 599>, `${res.status} ${res.statusText}`);
	}
	const json = await res.json();
	return json.results;
};

export const load = (async ({ fetch }) => {
	return {
		title: m.xRays(),
		stream: {
			data: getQualityCheckData(fetch)
		}
	};
}) satisfies PageServerLoad;
