import { BASE_API_URL } from '$lib/utils/constants';
import { contentDispositionHeader } from '$lib/utils/contentDisposition';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, setHeaders, params }) => {
	const endpoint = `${BASE_API_URL}/data-wizard/templates/${params.model}/`;

	const templateResponse = await fetch(endpoint);

	if (!templateResponse.ok || !templateResponse.body) {
		return error(templateResponse.status === 404 ? 404 : 500, 'Failed to fetch import template');
	}

	const contentType = templateResponse.headers.get('Content-Type') || 'application/octet-stream';
	const contentDisposition = templateResponse.headers.get('Content-Disposition');
	const fileName = contentDisposition?.split('filename=')[1]?.replace(/"/g, '').trim();

	if (!fileName) {
		return error(500, 'Invalid template response');
	}

	setHeaders({
		'Content-Type': contentType,
		'Content-Disposition': contentDispositionHeader(fileName)
	});

	return new Response(templateResponse.body);
};
