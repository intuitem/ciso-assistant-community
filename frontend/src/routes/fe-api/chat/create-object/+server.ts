import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

const SLUG_RE = /^[a-z0-9-/]+$/;

export const POST: RequestHandler = async ({ fetch, request }) => {
	let body: Record<string, unknown>;
	try {
		body = await request.json();
	} catch {
		return new Response(JSON.stringify({ detail: 'Invalid JSON' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const { url_slug, fields } = body as Record<string, any>;

	if (!url_slug || !fields) {
		return new Response(JSON.stringify({ detail: 'Missing url_slug or fields' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	if (!SLUG_RE.test(url_slug)) {
		return new Response(JSON.stringify({ detail: 'Invalid slug format' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const res = await fetch(`${BASE_API_URL}/${url_slug}/`, {
		method: 'POST',
		body: JSON.stringify(fields),
		headers: {
			'Content-Type': 'application/json'
		}
	});

	const responseData = await res.text();

	return new Response(responseData, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};
