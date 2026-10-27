import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// Whether accepting this form always takes a review (the backend checks the right).
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const { always_review } = await request.json();
	const res = await fetch(`${BASE_API_URL}/quick-forms/${params.id}/always-review/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ always_review })
	});
	return Response.json(await res.json().catch(() => ({})), { status: res.status });
};
