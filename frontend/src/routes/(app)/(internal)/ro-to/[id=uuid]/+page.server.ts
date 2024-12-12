import { loadDetail } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { getModelInfo } from '$lib/utils/crud';

export const load: PageServerLoad = async (event) => {
	return await loadDetail({ event, model: getModelInfo('ro-to'), id: event.params.id });
};

// export const actions: Actions = {
// 	default: async (event) => {
// 		return defaultWriteFormAction({ event, urlModel: 'ebios-rm', action: 'edit' });
// 	create: async (event) => {
// 		return defaultWriteFormAction({
// 			event,
// 			urlModel: 'assets',
// 			action: 'create'
// 		});
// 	},
// 	delete: async (event) => {
// 		return defaultDeleteFormAction({ event, urlModel: 'assets' });
// 	}
// };
