import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// `requirement-assessments` is a static route tree, so the generic
// `[model=urlmodel]` proxy never sees this path — it needs its own handler.
export const POST: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/requirement-assessments/${params.id}/findings-binder/`;

	const res = await fetch(endpoint, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: '{}'
	});
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
	});
};
