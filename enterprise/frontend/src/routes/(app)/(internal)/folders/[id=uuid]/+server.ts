import { BASE_API_URL } from '#lib/utils/constants.js';

import { type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

// This directory holds a page only, so it shadows [model=urlmodel]/[id=uuid]/+server.ts
// and every non-GET method 405s without a handler here. No GET: the page keeps it.

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const res = await fetch(`${BASE_API_URL}/folders/${params.id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(await request.json())
	});
	if (!res.ok) {
		errorFromBody(res.status as NumericRange<400, 599>, await res.json());
	}
	return new Response(JSON.stringify(await res.json()), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
