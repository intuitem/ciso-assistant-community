import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const endpoint = `${BASE_API_URL}/security-advisories/${params.id}/${
		url.searchParams.size > 0 ? '?' + url.searchParams.toString() : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const endpoint = `${BASE_API_URL}/security-advisories/${params.id}/`;

	const body = await request.json();
	const res = await fetch(endpoint, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
