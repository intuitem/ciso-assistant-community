import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	return loadDetail({ event, model: getModelInfo('folders'), id: event.params.id });
};
