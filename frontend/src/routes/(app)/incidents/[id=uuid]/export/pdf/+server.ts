import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'incidents';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/pdf/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the PDF file');
	}

	const fileName = `incident-${params.id}.pdf`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/pdf',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
