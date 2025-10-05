import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const endpoint = `${BASE_API_URL}/ebios-rm/studies/${params.id}/report-data/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return {
		reportData: data
	};
};
