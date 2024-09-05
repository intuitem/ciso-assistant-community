import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'applied-controls';
	const endpoint = `${BASE_API_URL}/${URLModel}/export_csv/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the CSV file');
	}

	const fileName = `applied-controls-${new Date().toISOString()}.csv`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'text/csv',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
