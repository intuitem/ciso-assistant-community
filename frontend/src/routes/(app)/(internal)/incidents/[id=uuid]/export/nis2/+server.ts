import { BASE_API_URL } from '#lib/utils/constants.js';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/incidents/${params.id}/nis2_notification/`);
	if (!res.ok) {
		error(400, 'Error fetching the PDF file');
	}
	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/pdf',
			'Content-Disposition': `attachment; filename="nis2-notification-${params.id}.pdf"`
		}
	});
};
