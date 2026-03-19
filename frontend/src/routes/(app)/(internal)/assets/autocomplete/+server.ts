import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const endpoint = `${BASE_API_URL}/assets/autocomplete/${
		url.searchParams.size ? '?' + url.searchParams.toString() : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		const body = await res.text();
		let parsed: unknown;
		try {
			parsed = JSON.parse(body);
		} catch {
			parsed = body;
		}
		error(res.status as NumericRange<400, 599>, parsed as any);
	}
	return new Response(res.body, {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
