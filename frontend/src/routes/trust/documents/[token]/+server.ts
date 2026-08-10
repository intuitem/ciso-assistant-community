import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, fetch }) => {
	const res = await fetch(`${BASE_API_URL}/public/documents/${params.token}/`);
	if (!res.ok) error(res.status === 404 ? 404 : 502, 'Not found');
	const headers = new Headers();
	for (const h of ['content-type', 'content-disposition', 'content-length']) {
		const v = res.headers.get(h);
		if (v) headers.set(h, v);
	}
	return new Response(res.body, { status: 200, headers });
};
