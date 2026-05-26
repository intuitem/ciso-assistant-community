import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * Multipart upload proxy. The entry page uses this for the
 * "Upload to folder" mode before chaining into start-audit-prefill.
 * Mirrors evidence-bulk-upload's proxy: re-issues the FormData rather
 * than streaming the raw body (handleFetch would corrupt the boundary).
 */
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
	return json(body, { status: res.status });
};
