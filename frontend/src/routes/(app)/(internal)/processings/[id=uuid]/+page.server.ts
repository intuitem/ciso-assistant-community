import { getModelInfo } from '$lib/utils/crud';
import { loadDetail, loadValidationFlowFormData } from '$lib/utils/load';
import type { PageServerLoad } from './$types';
import { fail, redirect, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import { BASE_API_URL } from '$lib/utils/constants';
import { setFlash } from 'sveltekit-flash-message/server';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('processings'),
		id: event.params.id
	});

	const { validationFlowForm, validationFlowModel } = await loadValidationFlowFormData({
		event,
		folderId: detailData.data.folder?.id || detailData.data.folder,
		targetField: 'processings',
		targetIds: [event.params.id]
	});

	return {
		...detailData,
		validationFlowForm,
		validationFlowModel
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	},
	startScreening: async (event) => {
		const res = await event.fetch(
			`${BASE_API_URL}/privacy/processings/${event.params.id}/dpia-screening/`,
			{ method: 'POST' }
		);
		const body = await res.json().catch(() => ({}));
		if (!res.ok) {
			setFlash(
				{
					type: 'error',
					message:
						String(body?.error) === 'screeningLibraryNotLoaded'
							? m.dpiaScreeningLibraryNotLoaded()
							: m.dpiaScreeningFailed()
				},
				event
			);
			return fail(res.status);
		}
		redirect(303, body.redirect);
	}
};
