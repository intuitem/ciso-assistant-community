import { BASE_API_URL } from '#lib/utils/constants.js';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const setUrn = url.searchParams.get('set_urn') ?? '';
	const res = await fetch(
		`${BASE_API_URL}/library-drafts/${params.id}/mapping-editor/?set_urn=${encodeURIComponent(setUrn)}`
	);
	if (!res.ok) {
		throw error(res.status, 'Mapping set not found in this draft');
	}
	return { draftId: params.id, editor: await res.json() };
};
