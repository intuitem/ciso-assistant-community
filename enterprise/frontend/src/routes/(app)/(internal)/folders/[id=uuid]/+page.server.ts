import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import {
	nestedDeleteFormAction,
	nestedWriteFormAction,
} from '$lib/utils/actions';

import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	return loadDetail({ event, model: getModelInfo('folders'), id: event.params.id });
};

export const actions: Actions = {
	create: async (event) => {
		const redirectToWrittenObject = false;
		return nestedWriteFormAction({ event, action: 'create', redirectToWrittenObject });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
};

