import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/pptx_report/`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the PPTX file');
	}

	const fileName = `audit-exec-summary-${new Date().toISOString()}.pptx`;

	return new Response(res.body, {
		headers: {
			'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
			'Content-Disposition': `attachment; filename="${fileName}"`,
			'Transfer-Encoding': 'chunked'
		}
	});
};
