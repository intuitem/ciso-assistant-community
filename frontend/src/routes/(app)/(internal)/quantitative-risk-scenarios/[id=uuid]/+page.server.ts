import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
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

	// Return the data
	return {
		...detailData
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
