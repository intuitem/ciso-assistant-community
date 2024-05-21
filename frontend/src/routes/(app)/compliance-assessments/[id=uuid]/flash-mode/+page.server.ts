import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';

export const load = (async ({ fetch, params }) => {
	const URLModel = 'compliance-assessments';
	const endpoint = `${BASE_API_URL}/${URLModel}/${params.id}/`;

	const res = await fetch(endpoint);
	const compliance_assessment = await res.json();

	const requirement_assessments = await fetch(`${endpoint}flash_mode/`).then((res) => res.json());

	return {
		URLModel,
		compliance_assessment,
		requirement_assessments
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	updateRequirementAssessment: async (event) => {
		const formData = await event.request.formData();
		const values: {id: string, status: string} = {id: '', status: ''};
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
