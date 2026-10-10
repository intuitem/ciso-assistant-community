import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const upstream = await fetch(`${BASE_API_URL}/chat/questionnaire-runs/${params.id}/export/`);

	if (!upstream.ok) {
		const data = await upstream.json().catch(() => ({}));
		return new Response(JSON.stringify(data), {
			status: upstream.status,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const headers = new Headers();
	const ct = upstream.headers.get('Content-Type');
	if (ct) headers.set('Content-Type', ct);
	const cd = upstream.headers.get('Content-Disposition');
	if (cd) headers.set('Content-Disposition', cd);

	return new Response(upstream.body, { status: 200, headers });
};
