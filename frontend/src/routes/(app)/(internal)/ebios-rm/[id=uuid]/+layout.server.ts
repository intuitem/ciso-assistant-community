import { loadDetail } from '#lib/utils/load.js';
import type { PageServerLoad } from './$types';
import { getModelInfo } from '#lib/utils/crud.js';

export const load: PageServerLoad = async (event) => {
	return await loadDetail({ event, model: getModelInfo('ebios-rm'), id: event.params.id });
};
