import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const endpoint = `${BASE_API_URL}/automation/posture-assessments/${event.params.id}`;
	const [detailData, posture, actionPlan] = await Promise.all([
		loadDetail({
			event,
			model: getModelInfo('posture-assessments'),
			id: event.params.id
		}),
		event.fetch(`${endpoint}/posture/`).then((res) => res.json()),
		event.fetch(`${endpoint}/action-plan/`).then((res) => res.json())
	]);

	return { ...detailData, posture, actionPlan };
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	createFinding: async (event) => {
		const formData = await event.request.formData();
		const res = await event.fetch(
			`${BASE_API_URL}/automation/posture-assessments/${event.params.id}/create-finding/`,
			{
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					requirement: formData.get('requirement'),
					asset: formData.get('asset')
				})
			}
		);
		if (!res.ok) return fail(res.status, await res.json());
		return { createdFinding: await res.json() };
	}
};
