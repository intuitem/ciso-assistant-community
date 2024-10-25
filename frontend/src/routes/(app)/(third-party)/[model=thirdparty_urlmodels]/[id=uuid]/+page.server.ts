import { nestedDeleteFormAction, nestedWriteFormAction } from '$lib/utils/actions';
import { type Actions } from '@sveltejs/kit';

export const actions: Actions = {
	create: async (event) => {
		return nestedWriteFormAction({ event, action: 'create' });
	},
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
