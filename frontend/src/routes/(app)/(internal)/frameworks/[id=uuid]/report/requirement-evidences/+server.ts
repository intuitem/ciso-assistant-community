import { BASE_API_URL } from '#lib/utils/constants.js';
import {
	contentDispositionHeader,
	parseContentDispositionFilename
} from '#lib/utils/contentDisposition.js';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const FORWARDED = [
	'requirement',
	'compliance_assessments',
	'exclude',
	'requirement_assessments',
	'implementation_group'
];

function zipResponse(res: Response): Response {
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
}

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const endpoint = new URL(`${BASE_API_URL}/frameworks/${params.id}/requirement_evidences/`);
	for (const key of FORWARDED) {
		for (const value of url.searchParams.getAll(key)) endpoint.searchParams.append(key, value);
	}
	return zipResponse(await fetch(endpoint.toString()));
};

export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const body = await request.json().catch(() => null);
	if (!body || typeof body !== 'object') throw error(400, 'Invalid selection');
	const selection = Object.fromEntries(FORWARDED.filter((k) => k in body).map((k) => [k, body[k]]));
	return zipResponse(
		await fetch(`${BASE_API_URL}/frameworks/${params.id}/requirement_evidences/`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(selection)
		})
	);
};
