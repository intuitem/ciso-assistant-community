import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const endpoint = `${BASE_API_URL}/task-templates/yearly_review/`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { folders: data };
};
