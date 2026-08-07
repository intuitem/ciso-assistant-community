import { BASE_API_URL } from '$lib/utils/constants';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, locals }) => {
	if (!locals.featureflags?.document_management) redirect(302, '/');
	const res = await fetch(`${BASE_API_URL}/document-templates/${params.id}/`);
	if (!res.ok) error(res.status, 'Template not found');
	const template = await res.json();
	return { template };
};
