import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	// Load the quantitative risk scenario details
	const detailData = await loadDetail({
		event,
		model: getModelInfo('quantitative-risk-scenarios'),
		id: event.params.id
	});

	// Fetch LEC data for the scenario
	const lecData = await event
		.fetch(
			`${BASE_API_URL}/crq/quantitative-risk-scenarios/${event.params.id}/lec/?t=${Date.now()}`
		)
		.then((res) => res.json())
		.catch(() => ({ curves: [] }));

	// Return the combined data
	return {
		...detailData,
		lec: lecData
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
