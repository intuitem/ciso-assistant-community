import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/entities/export_ecosystem/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the TPRM ecosystem export');
	}

	const fileName = `tprm-ecosystem-${new Date().toISOString().split('T')[0]}.xlsx`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
