import { BASE_API_URL } from '$lib/utils/constants';

import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
export const GET: RequestHandler = async ({ fetch, url }) => {
	const riskAssessmentId = url.searchParams.get('risk_assessment');
	const endpoint = `${BASE_API_URL}/risk-scenarios/default_ref_id/?risk_assessment=${riskAssessmentId}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(400, 'Failed to fetch default ref_id');
	}
	const logo = await res.json();

	return new Response(JSON.stringify(logo), {
		headers: {
			'Content-Type': 'application/json'
		}
	});
};
