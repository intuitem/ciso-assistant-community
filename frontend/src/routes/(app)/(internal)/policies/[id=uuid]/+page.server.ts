import { getModelInfo } from '$lib/utils/crud';
import { loadDetail, loadValidationFlowFormData } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	const detailData = await loadDetail({
		event,
		model: getModelInfo('policies'),
		id: event.params.id
	});

	const { validationFlowForm, validationFlowModel } = await loadValidationFlowFormData({
		event,
		folderId: detailData.data.folder?.id || detailData.data.folder,
		targetField: 'policies',
		targetIds: [event.params.id]
	});

	// Load policy document + current revision for inline preview
	let policyDocument = null;
	let currentRevisionContent = null;
	try {
		const docRes = await event.fetch(
			`${BASE_API_URL}/managed-documents/?policy=${event.params.id}`
		);
		if (docRes.ok) {
			const docData = await docRes.json();
			policyDocument = docData.results?.[0] || null;
			if (policyDocument?.current_revision?.id) {
				const revRes = await event.fetch(
					`${BASE_API_URL}/document-revisions/${policyDocument.current_revision.id}/`
				);
				if (revRes.ok) {
					currentRevisionContent = await revRes.json();
				}
			}
		}
	} catch {
		// Silently ignore — document feature is optional
	}

	return {
		...detailData,
		validationFlowForm,
		validationFlowModel,
		policyDocument,
		currentRevisionContent
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
