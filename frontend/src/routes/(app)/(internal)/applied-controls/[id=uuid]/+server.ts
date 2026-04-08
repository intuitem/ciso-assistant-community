import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const endpoint = `${BASE_API_URL}/applied-controls/${params.id}/`;

	const body = await request.json();
	const res = await fetch(endpoint, {
		method: 'PATCH',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
