import { BASE_API_URL } from '$lib/utils/constants';
import { languageTag } from '$paraglide/runtime';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'risk-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/risk_assessment_pdf/`;

	const risk_assessment = await fetch(`${BASE_API_URL}/${URLModel}/${params.id}/`).then((res) =>
		res.json()
	);

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the PDF file');
	}

	const fileName = `RA-${risk_assessment.name}-${
		risk_assessment.version
	}-${new Date().toISOString()}.pdf`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'text/pdf',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
