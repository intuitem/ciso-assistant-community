import { BASE_API_URL } from '$lib/utils/constants';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const endpoint = `${BASE_API_URL}/custom-word-templates/download-default/${params.template_key}/${params.language}/`;
	const res = await fetch(endpoint);

	return new Response(res.body, {
		status: res.status,
		headers: {
			'Content-Type':
				res.headers.get('Content-Type') ??
				'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
			'Content-Disposition': res.headers.get('Content-Disposition') ?? ''
		}
	});
};
