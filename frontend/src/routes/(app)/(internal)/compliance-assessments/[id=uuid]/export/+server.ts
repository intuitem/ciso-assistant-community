import { BASE_API_URL } from '$lib/utils/constants';

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

	const originalFileName = `${compliance_assessment.name}-${
		compliance_assessment.framework.str
	}-${new Date().toISOString()}.zip`;
	const sanitizedFilename = originalFileName.replace(/[^\x01-\xFF]/g, '');

	const blobData = await res.blob();
	return new Response(blobData, {
		headers: {
			'Content-Type': 'application/zip',
			'Content-Disposition': `attachment; filename="${sanitizedFilename}"`
		}
	});
};
