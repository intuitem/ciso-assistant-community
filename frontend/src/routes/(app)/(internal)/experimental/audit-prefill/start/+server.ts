import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * Start an audit-prefill Wave 1 run. Used by the entry page so submission
 * can be pure JS (no form-action redirect) — that's what lets us run the
 * upload step first in upload-mode without racing with use:enhance.
 *
 * Body: { folder, compliance_assessment, strictness }
 * Returns the backend response verbatim ({ id, status } on success).
 */
export const POST: RequestHandler = async ({ request, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const res = await fetch(`${BASE_API_URL}/chat/agent-runs/start-audit-prefill/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			folder: body.folder,
			compliance_assessment: body.compliance_assessment,
			strictness: body.strictness ?? 'fast'
		})
	});
	const data = await res.json().catch(() => ({}));
	return json(data, { status: res.status });
};
