import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const endpoint = `${BASE_API_URL}/applied-controls/autocomplete/${
		url.searchParams.size ? '?' + url.searchParams.toString() : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		const body = await res.text();
		try {
			error(res.status as NumericRange<400, 599>, JSON.parse(body));
		} catch {
			error(res.status as NumericRange<400, 599>, body);
		}
	}
	return new Response(res.body, {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
