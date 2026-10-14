import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request }) => {
	const res = await fetch(`${BASE_API_URL}/metrology/metric-definitions/preview-formula/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: await request.text()
	});
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
