import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

// Preflight preview: lets the selection modal validate that a mapping path
// exists (and show the error inline) before navigating to the preview page.
export const GET: RequestHandler = async (event) => {
	const sourceAuditId = event.url.searchParams.get('source_audit_id') ?? '';
	const endpoint = `${BASE_API_URL}/compliance-assessments/${event.params.id}/map_from_preview/?source_audit_id=${sourceAuditId}`;
	const res = await event.fetch(endpoint);

	const payload = await res.text();
	return new Response(payload, {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};

export const POST: RequestHandler = async (event) => {
	const body = await event.request.text();
	const endpoint = `${BASE_API_URL}/compliance-assessments/${event.params.id}/map_from/`;
	const res = await event.fetch(endpoint, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body
	});

	if (!res.ok) {
		const response = await res.json();
		console.error(response);
		return new Response(JSON.stringify(response), {
			status: res.status,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	return new Response(JSON.stringify(await res.json()), {
		headers: { 'Content-Type': 'application/json' }
	});
};
