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
		const formData = await event.request.formData();
		const values: { id: string; result: string } = { id: '', result: '' };
		for (const entry of formData.entries()) {
			values[entry[0]] = entry[1];
		}
		const URLModel = 'requirement-assessments';
		const endpoint = `${BASE_API_URL}/${URLModel}/${values.id}/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(values)
		};

		await event.fetch(endpoint, requestInitOptions);
	}
};
