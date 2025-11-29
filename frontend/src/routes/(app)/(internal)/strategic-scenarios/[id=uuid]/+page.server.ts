import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	return await loadDetail({
		event,
		model: getModelInfo('strategic-scenarios'),
		id: event.params.id
	});
};
