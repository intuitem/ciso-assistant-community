import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const compliance_assessment = await res.json();

	const flashMode = await fetch(`${endpoint}flash_mode/`).then((res) => res.json());

	const requirement_assessments = flashMode.requirement_assessments;
	const requirements = flashMode.requirements;

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

		await event.fetch(endpoint, requestInitOptions);
	}
};
