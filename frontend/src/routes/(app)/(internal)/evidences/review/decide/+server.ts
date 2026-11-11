import { BASE_API_URL } from '#lib/utils/constants.js';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const UUID = /^[0-9a-f-]{36}$/i;

export const POST: RequestHandler = async ({ fetch, request }) => {
	const { revision, decision, comment, seen } = await request.json();
	if (!UUID.test(String(revision))) error(400, 'invalid revision');
	const res = await fetch(`${BASE_API_URL}/evidence-revisions/${revision}/review/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ decision, comment, seen })
	});
	return json(await res.json().catch(() => ({})), { status: res.status });
};
