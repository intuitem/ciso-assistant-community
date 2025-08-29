import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	// Keep your existing loadDetail logic
	const detailData = await loadDetail({
		event,
		model: getModelInfo('quantitative-risk-hypotheses'),
		id: event.params.id
	});

	const lecData = await event
		.fetch(`${BASE_API_URL}/crq/quantitative-risk-hypotheses/${event.params.id}/lec/`)
		.then((res) => res.json());
	return {
		...detailData,
		lec: lecData
	};
};
export const actions: Actions = {
	delete: async (event) => {
		console.log('delete');
		return nestedDeleteFormAction({ event });
	}
};
