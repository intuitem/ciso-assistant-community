import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'frameworks';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/excel_template/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the Excel file');
	}

	const fileName = `framework-${params.id}-.xlsx`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			'Content-Disposition': `attachment`
		}
	});
};
