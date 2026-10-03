import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const TIER_TARGET = 'entity.tier';

// The publications the caller may file that set an entity's tier.
export const GET: RequestHandler = async ({ fetch }) => {
	const res = await fetch(`${BASE_API_URL}/quick-form-publications/mine/`);
	if (!res.ok) return json([]);
	const rows = (await res.json()) as { id: string; name: string; targets?: string[] }[];
	return json(
		rows
			.filter((row) => (row.targets ?? []).includes(TIER_TARGET))
			.map((row) => ({ id: row.id, name: row.name }))
	);
};

// Start (or resume) an assessment of this entity through one of them.
export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const { publication } = await request.json();
	const res = await fetch(`${BASE_API_URL}/quick-form-publications/${publication}/start/`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ subject: params.id })
	});
	return json(await res.json(), { status: res.status });
};
