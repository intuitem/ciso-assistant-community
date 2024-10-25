import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async (event) => {
	return await loadDetail({ event, model: getModelInfo(event.params.model), id: event.params.id });
};
