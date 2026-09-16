import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async (event) => {
	const endpoint = `${BASE_API_URL}/compliance-assessments/${event.params.id}/global_score/`;
	const res = await event.fetch(endpoint);
	return new Response(await res.text(), {
		status: res.status,
		headers: { 'Content-Type': res.headers.get('Content-Type') ?? 'application/json' }
	});
};
