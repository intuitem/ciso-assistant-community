import { BASE_API_URL } from '$lib/utils/constants';
import { languageTag } from '$paraglide/runtime';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'risk-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/treatment_plan_pdf/`;

	const res = await fetch(endpoint, {
		headers: {
			'Accept-Language': languageTag()
		}
	});
	if (!res.ok) {
		error(400, 'Error fetching the PDF file');
	}

	const fileName = `TP-${params.id}-${new Date().toISOString()}.pdf`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'text/pdf',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
