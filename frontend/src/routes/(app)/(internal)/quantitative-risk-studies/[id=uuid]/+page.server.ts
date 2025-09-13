import { getModelInfo } from '$lib/utils/crud';
import { loadDetail } from '$lib/utils/load';
import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { fail, type Actions } from '@sveltejs/kit';
import { nestedDeleteFormAction } from '$lib/utils/actions';

export const load: PageServerLoad = async (event) => {
	// Keep your existing loadDetail logic
	const detailData = await loadDetail({
		event,
		model: getModelInfo('quantitative-risk-studies'),
		id: event.params.id
	});

	// Fetch combined ALE data
	let combinedAleData = null;
	try {
		const url = `${BASE_API_URL}/crq/quantitative-risk-studies/${event.params.id}/combined-ale/`;
		const response = await event.fetch(url);
		if (response.ok) {
			combinedAleData = await response.json();
		}
	} catch (error) {
		console.warn('Failed to fetch combined ALE data:', error);
	}

	// Fetch combined LEC data
	let combinedLecData = null;
	try {
		const url = `${BASE_API_URL}/crq/quantitative-risk-studies/${event.params.id}/combined-lec/`;
		const response = await event.fetch(url);
		if (response.ok) {
			combinedLecData = await response.json();
		}
	} catch (error) {
		console.warn('Failed to fetch combined LEC data:', error);
	}

	// Return the original data plus combined data
	return {
		...detailData,
		combinedAle: combinedAleData,
		combinedLec: combinedLecData
	};
};

export const actions: Actions = {
	delete: async (event) => {
		return nestedDeleteFormAction({ event });
	}
};
