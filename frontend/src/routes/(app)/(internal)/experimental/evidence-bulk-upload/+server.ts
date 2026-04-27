import { BASE_API_URL } from '$lib/utils/constants';
import { error, json, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Forwards the multipart batch-upload payload to the Django backend.
// Re-builds FormData with concrete Blobs so the inner fetch serialises it correctly
// (matches the policy document upload-image proxy pattern).
export const POST: RequestHandler = async ({ request, fetch }) => {
	const incoming = await request.formData();
	const outgoing = new FormData();
	for (const [key, value] of incoming.entries()) {
		if (value instanceof File) {
			const bytes = new Uint8Array(await value.arrayBuffer());
			outgoing.append(key, new Blob([bytes], { type: value.type }), value.name);
		} else {
			outgoing.append(key, value as string);
		}
	}

	const res = await fetch(`${BASE_API_URL}/evidences/batch-upload/`, {
		method: 'POST',
		body: outgoing
	});

	const text = await res.text();
	let body: unknown;
	try {
		body = JSON.parse(text);
	} catch {
		body = { error: text };
	}

	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, body as App.Error);
	}
	return json(body, { status: res.status });
};
