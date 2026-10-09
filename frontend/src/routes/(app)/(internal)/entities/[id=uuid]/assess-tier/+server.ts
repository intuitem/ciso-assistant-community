import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const TIER_TARGET = 'entity.tier';

// What the caller can start to set this entity's tier: forms they may fill
// in-house, else publications they may file against.
export const GET: RequestHandler = async ({ fetch, params }) => {
	const query = new URLSearchParams({ target: TIER_TARGET, subject: params.id });
	const res = await fetch(`${BASE_API_URL}/quick-forms/assess-options/?${query}`);
	return json(res.ok ? await res.json() : []);
};

// Start (or resume) an assessment of this entity through one of them.
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const { kind, id } = await request.json();
	const base = kind === 'form' ? 'quick-forms' : 'quick-form-publications';
	const res = await fetch(`${BASE_API_URL}/${base}/${id}/start/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ subject: params.id })
	});
	return json(await res.json().catch(() => ({})), { status: res.status });
};
