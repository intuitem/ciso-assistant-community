import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';

// Start the asset's next homologation cycle, or freeze its deliverables.
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const { step } = await request.json();
	const res = await fetch(`${BASE_API_URL}/assets/${params.id}/accreditation-cycle/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ step })
	});
	return Response.json(await res.json().catch(() => ({})), { status: res.status });
};
