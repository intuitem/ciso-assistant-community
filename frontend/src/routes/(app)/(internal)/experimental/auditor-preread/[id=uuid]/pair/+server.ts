import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

/** Mark or unmark an evidence as answering one auditor request. */
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const res = await fetch(
		`${BASE_API_URL}/compliance-assessments/${params.id}/auditor_preread/pair/`,
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
