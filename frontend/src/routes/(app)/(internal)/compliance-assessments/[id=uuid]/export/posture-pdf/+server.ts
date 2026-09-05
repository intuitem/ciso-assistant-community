import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Kept in step with REPORT_PROFILES in backend/core/generators.py; the backend
// rejects anything else, this just avoids forwarding junk.
const PROFILES = ['full', 'attestation'];

export const GET: RequestHandler = async ({ fetch, params, url }) => {
	const requested = url.searchParams.get('profile') ?? 'full';
	const profile = PROFILES.includes(requested) ? requested : 'full';

	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/posture-pdf/?profile=${profile}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Error fetching the PDF file');
	}

	const fileName = `audit-${profile}-${new Date().toISOString()}.pdf`;

	return new Response(res.body, {
		headers: {
			'Content-Type': 'application/pdf',
			'Content-Disposition': `attachment; filename="${fileName}"`,
			'Transfer-Encoding': 'chunked'
		}
	});
};
