import { BASE_API_URL, UUID_LIST_REGEX } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const params = url.searchParams;
	if (!params.has('risk_assessment')) {
		error(400, 'No risk_assessment found in the URL !');
	}

	const risk_assessment_string = params.get('risk_assessment');
	if (risk_assessment_string && !UUID_LIST_REGEX.test(risk_assessment_string)) {
		error(400, 'Invalid risk_assessment UUID list');
	}

	const req: Response = await fetch(
		`${BASE_API_URL}/composer_data/?risk_assessment=${risk_assessment_string}`
	);

	const resp = await req.json();

	if (resp.error) {
		error(req.status, resp.error);
	}

	return resp.result;
};
