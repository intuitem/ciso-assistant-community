import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// The screening by default; `?target=processing.dpia` for the DPIA itself.
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const TARGETS = ['processing.dpia_required', 'processing.dpia'];

// What the caller can start on this processing: forms they may fill in-house,
// else publications they may file against.
export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const target = url.searchParams.get('target');
	const query = new URLSearchParams({
		target: target && TARGETS.includes(target) ? target : TARGETS[0],
		subject: params.id
	});
	const res = await fetch(`${BASE_API_URL}/quick-forms/assess-options/?${query}`);
	return json(res.ok ? await res.json() : []);
};

// Start (or resume) a screening of this processing through one of them.
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const { kind, id } = await request.json().catch(() => ({}));
	// Both go into the backend path: only a known kind and a UUID.
	if (!['form', 'publication'].includes(kind) || typeof id !== 'string' || !UUID.test(id)) {
		return json({ error: 'invalidRequest' }, { status: 400 });
	}
	const base = kind === 'form' ? 'quick-forms' : 'quick-form-publications';
	const res = await fetch(`${BASE_API_URL}/${base}/${id}/start/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ subject: params.id })
	});
	return json(await res.json().catch(() => ({})), { status: res.status });
};
