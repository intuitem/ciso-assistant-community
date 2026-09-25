import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url }) => {
	const queryString = url.searchParams.toString();
	const endpoint = `${BASE_API_URL}/log-entries/export_xlsx/${queryString ? '?' + queryString : ''}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the XLSX file');
	}

	const fileName = `audit-log-${new Date().toISOString().split('T')[0]}.xlsx`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
