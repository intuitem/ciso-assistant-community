import { BASE_API_URL } from '#lib/utils/constants.js';
import { discardBody } from '#lib/utils/responses.js';
import { getModelInfo } from '#lib/utils/crud.js';
import { loadDetail } from '#lib/utils/load.js';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';
import { defaultDeleteFormAction, defaultWriteFormAction } from '#lib/utils/actions.js';

export const load: PageServerLoad = async (event) => {
	// read-only preview: the graph endpoint is enough, the palette needs no catalog here
	const [detail, graph] = await Promise.all([
		loadDetail({ event, model: getModelInfo('threat-models'), id: event.params.id }),
		event
			.fetch(`${BASE_API_URL}/threat-models/${event.params.id}/graph/`)
			.then((res) => (res.ok ? res.json() : discardBody(res).then(() => null)))
	]);

	return { ...detail, graph };
};

export const actions: Actions = {
	create: async (event) =>
		defaultWriteFormAction({ event, urlModel: 'threat-models', action: 'create' }),
	edit: async (event) =>
		defaultWriteFormAction({ event, urlModel: 'threat-models', action: 'edit' }),
	delete: async (event) => defaultDeleteFormAction({ event, urlModel: 'threat-models' })
};
