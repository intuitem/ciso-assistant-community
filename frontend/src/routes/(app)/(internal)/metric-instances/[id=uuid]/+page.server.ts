import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('metric-instances'),
		id: event.params.id
	});

	return detailData;
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
