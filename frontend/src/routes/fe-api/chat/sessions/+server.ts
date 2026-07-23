import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

const BACKEND_ERROR = JSON.stringify({ detail: 'Chat service unavailable' });

export const GET: RequestHandler = async ({ fetch, url }) => {
	try {
		// Forward query params so paging keeps working if this endpoint ever
		// returns a paginated envelope instead of a plain array.
		const res = await fetch(`${BASE_API_URL}/chat/sessions/${url.search}`);
		return new Response(await res.text(), {
			status: res.status,
			headers: { 'Content-Type': res.headers.get('Content-Type') ?? 'application/json' }
		});
	} catch {
		return new Response(BACKEND_ERROR, {
			status: 502,
			headers: { 'Content-Type': 'application/json' }
		});
	}
};

export const POST: RequestHandler = async ({ fetch, request }) => {
	try {
		const body = await request.text();
		const res = await fetch(`${BASE_API_URL}/chat/sessions/`, {
			method: 'POST',
			body,
			headers: { 'Content-Type': 'application/json' }
		});
		return new Response(await res.text(), {
			status: res.status,
			headers: { 'Content-Type': res.headers.get('Content-Type') ?? 'application/json' }
		});
	} catch {
		return new Response(BACKEND_ERROR, {
			status: 502,
			headers: { 'Content-Type': 'application/json' }
		});
	}
};
