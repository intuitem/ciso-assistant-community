import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async (event) => {
	const modelInfo = getModelInfo('assets');

	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	return data;
};
