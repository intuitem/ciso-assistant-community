import { BASE_API_URL } from '#lib/utils/constants.js';
import type { RequestHandler } from './$types';
import { errorFromBody } from '#lib/utils/errors.js';

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
		errorFromBody(res.status, body as App.Error);
	}
	return Response.json(body, { status: res.status });
};
