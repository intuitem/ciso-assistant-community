import { getModelInfo } from '#lib/utils/crud.js';
import { loadDetail } from '#lib/utils/load.js';
import { type Actions } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';
import { nestedDeleteFormAction } from '#lib/utils/actions.js';

const VENDOR_FIELDS = ['name', 'description', 'status', 'link', 'expiry_date', 'updated_at'];

export const load: PageServerLoad = async (event) => {
	const user = await event.locals.getUser();
	const model = getModelInfo('evidences');
	const vendorModel = {
		...model,
		reverseForeignKeyFields: model.reverseForeignKeyFields?.filter(
			(f) => f.urlModel === 'evidence-revisions'
		),
		detailViewFields: model.detailViewFields?.filter((f) => VENDOR_FIELDS.includes(f.field))
	};
	return await loadDetail({
		event,
		model: user?.is_third_party ? vendorModel : model,
		id: event.params.id
	});
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
