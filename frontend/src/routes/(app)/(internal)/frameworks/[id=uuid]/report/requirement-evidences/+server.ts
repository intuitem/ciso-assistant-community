import { BASE_API_URL } from '#lib/utils/constants.js';
import {
	contentDispositionHeader,
	parseContentDispositionFilename
} from '#lib/utils/contentDisposition.js';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const endpoint = new URL(`${BASE_API_URL}/frameworks/${params.id}/requirement_evidences/`);
	for (const key of ['requirement', 'compliance_assessments', 'exclude']) {
		const value = url.searchParams.get(key);
		if (value) endpoint.searchParams.set(key, value);
	}
	const res = await fetch(endpoint.toString());
	if (!res.ok) throw error(res.status, 'Error fetching the ZIP file');
	const fileName =
		parseContentDispositionFilename(res.headers.get('Content-Disposition') ?? '') ??
		'evidences.zip';
	return new Response(await res.blob(), {
		headers: {
			'Content-Type': 'application/zip',
			'Content-Disposition': contentDispositionHeader(fileName)
		}
	});
};
