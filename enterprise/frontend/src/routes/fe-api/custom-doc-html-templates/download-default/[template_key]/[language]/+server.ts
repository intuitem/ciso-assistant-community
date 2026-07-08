import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/custom-doc-html-templates/download-default/${encodeURIComponent(params.template_key)}/${encodeURIComponent(params.language)}/`;
	const res = await fetch(endpoint);

	return new Response(res.body, {
		status: res.status,
		headers: {
			'Content-Type': res.headers.get('Content-Type') ?? 'text/html',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? ''
		}
	});
};
