import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

/** Store one decision of this audit's preparation. */
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const res = await fetch(
		`${BASE_API_URL}/compliance-assessments/${params.id}/auditor_preread/preparation/`,
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(await request.json())
		}
	);
	return new Response(res.status === 204 ? null : await res.text(), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};
