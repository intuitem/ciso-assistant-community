import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;
	const objectEndpoint = `${endpoint}object`;

	const res = await fetch(endpoint);
	const compliance_assessment = await res.json();

	const object = await fetch(objectEndpoint).then((res) => res.json());

	const tree = await fetch(`${endpoint}tree/`).then((res) => res.json());

	const compliance_assessment_donut_values = await fetch(
		`${BASE_API_URL}/${URLModel}/${params.id}/donut_data/`
	).then((res) => res.json());

	const global_score = await fetch(`${BASE_API_URL}/${URLModel}/${params.id}/global_score/`).then(
		(res) => res.json()
	);

	return {
		URLModel,
		compliance_assessment,
		object,
		tree,
		compliance_assessment_donut_values,
		global_score
	};
}) satisfies PageServerLoad;
