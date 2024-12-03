import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const queryParams = url.searchParams.has('refresh') ? '?refresh=1' : '';
	redirect(301, `/analytics${queryParams}`);
};
