import { BASE_API_URL } from '$lib/utils/constants';
import { error, type NumericRange } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const res = await fetch(`${BASE_API_URL}/privacy/dpias/${params.id}/report/`);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	return { id: params.id, report: await res.json() };
};
