import { BASE_API_URL } from '#lib/utils/constants.js';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ request, fetch }) => {
	const fd = await request.formData();
	const res = await fetch(`${BASE_API_URL}/evidences/batch-upload/`, {
		method: 'POST',
		body: fd
	});

	const text = await res.text();
	let body: unknown;
	try {
		body = JSON.parse(text);
	} catch {
		body = { error: text };
	}

	if (!res.ok) {
		error(res.status, body as App.Error);
	}
	return json(body, { status: res.status });
};
