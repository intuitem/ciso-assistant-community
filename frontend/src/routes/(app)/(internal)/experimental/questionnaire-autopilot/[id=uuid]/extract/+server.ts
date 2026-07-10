import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(
		`${BASE_API_URL}/chat/questionnaire-runs/${params.id}/extract-questions/`,
		{ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }
	);
	const data = await res.json().catch(() => ({}));
	return json(data, { status: res.status });
};
