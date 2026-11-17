import { getModelInfo } from '#lib/utils/crud.js';
import { loadDetail } from '#lib/utils/load.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('service-accounts');

	return loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});
};
