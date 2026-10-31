import { type Actions } from '@sveltejs/kit';

import { defaultWriteFormAction } from '#lib/utils/actions.js';

export const actions: Actions = {
	default: async (event) => {
		return defaultWriteFormAction({ event, urlModel: event.params.model!, action: 'edit' });
	}
};
