import { BASE_API_URL } from '$lib/utils/constants';
import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, locals }) => {
	if (!locals.featureflags?.document_management) {
		redirect(302, '/');
	}
	const res = await fetch(`${BASE_API_URL}/document-containers/catalog/`);
	const catalog = res.ok ? await res.json() : [];

	const unpubRes = await fetch(
		`${BASE_API_URL}/document-containers/?status=draft&status=in_review&status=change_requested&status=validated&limit=1`
	);
	const unpublishedCount = unpubRes.ok ? ((await unpubRes.json()).count ?? 0) : 0;

	return { catalog, unpublishedCount };
};
