import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/loaded-libraries/${params.id}/preview-workflows/`);
	const data = await res.json().catch(() => ({}));
	return json(data, { status: res.status });
};
