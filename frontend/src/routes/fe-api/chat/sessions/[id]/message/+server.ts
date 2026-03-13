import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request, params }) => {
	const body = await request.text();
	const res = await fetch(`${BASE_API_URL}/chat/sessions/${params.id}/message/`, {
		method: 'POST',
		body,
		headers: {
			'Content-Type': 'application/json'
		}
	});

	// Forward the SSE stream
	if (!res.body) {
		return new Response('No response body', { status: 502 });
	}

	return new Response(res.body, {
		status: res.status,
		headers: {
			'Content-Type': 'text/event-stream',
			'Cache-Control': 'no-cache',
			Connection: 'keep-alive'
		}
	});
};
