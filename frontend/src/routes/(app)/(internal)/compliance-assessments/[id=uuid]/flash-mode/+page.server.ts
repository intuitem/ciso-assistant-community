import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const [compliance_assessment, flashMode] = await Promise.all(
		[endpoint, `${endpoint}requirements_list/`].map((endpoint) =>
			fetch(endpoint).then((res) => res.json())
		)
	);

	const requirement_assessments = flashMode.requirement_assessments;
	const requirements = flashMode.requirements;

	requirements.forEach((requirement) => {
		if (
			requirement.name &&
			requirement.name.indexOf("Compréhension de l'organisation et de son contexte") >= 0 &&
			requirement.description
		) {
			console.log(requirement);
		}
	});

	return {
		URLModel,
		compliance_assessment,
		requirement_assessments,
		requirements
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	updateRequirementAssessment: async (event) => {
		const data = await event.request.json();
		const value: { id: string; result: string } = data;
		const URLModel = 'requirement-assessments';
		const endpoint = `${BASE_API_URL}/${URLModel}/${value.id}/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(value)
		};

		const res = await event.fetch(endpoint, requestInitOptions);
		return { status: res.status, body: await res.json() };
	}
};
