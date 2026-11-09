import { BASE_API_URL } from '#lib/utils/constants.js';
import {
	contentDispositionHeader,
	parseContentDispositionFilename
} from '#lib/utils/contentDisposition.js';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const FORWARDED = ['requirement', 'compliance_assessments', 'exclude', 'implementation_group'];

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const endpoint = new URL(`${BASE_API_URL}/frameworks/${params.id}/requirement_evidences/`);
	for (const key of FORWARDED) {
		for (const value of url.searchParams.getAll(key)) endpoint.searchParams.append(key, value);
	}
	const res = await fetch(endpoint.toString());
	if (!res.ok || !res.body) throw error(res.status, 'Error fetching the ZIP file');
	const fileName =
		parseContentDispositionFilename(res.headers.get('Content-Disposition') ?? '') ??
		'evidences.zip';
	return new Response(res.body, {
		headers: {
			'Content-Type': 'application/zip',
			'Content-Disposition': contentDispositionHeader(fileName)
		}
	});
};
