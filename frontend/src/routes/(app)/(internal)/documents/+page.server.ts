import { BASE_API_URL } from '$lib/utils/constants';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (locals.featureflags?.document_management === false) {
		redirect(302, '/');
	}
	const res = await fetch(`${BASE_API_URL}/document-containers/catalog/`);
	const catalog = res.ok ? await res.json() : [];
	return { catalog };
};
