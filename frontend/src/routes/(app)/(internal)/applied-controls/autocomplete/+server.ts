import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const endpoint = `${BASE_API_URL}/applied-controls/autocomplete/${
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
		errorFromBody(res.status, parsed as any);
	}
	return new Response(res.body, {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
