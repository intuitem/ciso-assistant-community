import { BASE_API_URL } from '$lib/utils/constants';

import { error, type NumericRange } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// This static route shadows the generic [model=urlmodel]/[id=uuid] route (its
// +page.server.ts redirects to the editor), so the table's edit/delete client
// fetches to /document-containers/{id} need explicit method handlers here.

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/document-containers/${params.id}/`);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	const res = await fetch(`${BASE_API_URL}/document-containers/${params.id}/`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(await request.json())
	});
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: { 'Content-Type': 'application/json' }
	});
};

export const DELETE: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/document-containers/${params.id}/`, {
		method: 'DELETE'
	});
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.text());
	}
	return new Response(null, { status: res.status });
};
