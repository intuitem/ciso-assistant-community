import { BASE_API_URL } from '$lib/utils/constants';
import { languageTag } from '$paraglide/runtime';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/export/`;

	const compliance_assessment = await fetch(`${BASE_API_URL}/${URLModel}/${params.id}/`).then(
		(res) => res.json()
	);

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the ZIP file');
	}

	const fileName = `${compliance_assessment.name}-${
		compliance_assessment.framework.str
	}-${new Date().toISOString()}.zip`;

	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/zip',
			'Content-Disposition': `attachment; filename="${fileName}"`
		}
	});
};
