import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { nestedDeleteFormAction } from '$lib/utils/actions';
import type { Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { BASE_API_URL } from '$lib/utils/constants';

export const load: PageServerLoad = async (event) => {
	const modelInfo = getModelInfo('dora-incident-reports');
	const data = await loadDetail({
		event,
		model: modelInfo,
		id: event.params.id
	});

	// Fetch validation status
	const validationEndpoint = `${BASE_API_URL}/resilience/dora-incident-reports/${event.params.id}/validate_report/`;
	let validation = { valid: false, errors: [] };
	try {
		const res = await event.fetch(validationEndpoint);
		if (res.ok) {
			validation = await res.json();
		}
	} catch {
		// Validation is optional — don't block page load
	}

	return { ...data, validation };
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
