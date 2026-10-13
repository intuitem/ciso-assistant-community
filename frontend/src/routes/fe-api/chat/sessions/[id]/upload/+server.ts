import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, request, params }) => {
	// Rebuild the FormData: forwarding the raw stream loses the multipart
	// boundary (handleFetch forces application/json on passthrough bodies).
	const incoming = await request.formData();
	const file = incoming.get('file');

	if (!(file instanceof File)) {
		return new Response(JSON.stringify({ detail: 'No file provided.' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const forwarded = new FormData();
	forwarded.append('file', file, file.name);
	const folderId = incoming.get('folder_id');
	if (typeof folderId === 'string' && folderId) {
		forwarded.append('folder_id', folderId);
	}

	const res = await fetch(`${BASE_API_URL}/chat/sessions/${params.id}/upload/`, {
		method: 'POST',
		body: forwarded
	});

	const body = await res.text();
	return new Response(body, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'application/json'
		}
	});
};
