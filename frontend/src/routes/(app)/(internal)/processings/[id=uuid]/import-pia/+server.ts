import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Start a draft DPIA of this processing from a CNIL PIA export, parsed by the browser.
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const body = await request.json().catch(() => null);
	if (!body || typeof body !== 'object') {
		return json({ error: 'piaInvalidFile' }, { status: 400 });
	}
	const res = await fetch(`${BASE_API_URL}/privacy/processings/${params.id}/import-pia/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ quick_form: body.quick_form, pia: body.pia, labels: body.labels })
	});
	return json(await res.json().catch(() => ({})), { status: res.status });
};
