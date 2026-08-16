import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';
import { defaultDeleteFormAction, defaultWriteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	// read-only preview: the graph endpoint is enough, the palette needs no catalog here
	const [detail, res] = await Promise.all([
		loadDetail({ event, model: getModelInfo('threat-models'), id: event.params.id }),
		event.fetch(`${BASE_API_URL}/threat-models/${event.params.id}/graph/`)
	]);
	const graph = res.ok ? await res.json() : null;

	return { ...detail, graph };
};

export const actions: Actions = {
	create: async (event) =>
		defaultWriteFormAction({ event, urlModel: 'threat-models', action: 'create' }),
	edit: async (event) =>
		defaultWriteFormAction({ event, urlModel: 'threat-models', action: 'edit' }),
	delete: async (event) => defaultDeleteFormAction({ event, urlModel: 'threat-models' })
};
