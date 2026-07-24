import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params, url }) => {
	const draftRes = await fetch(`${BASE_API_URL}/library-drafts/${params.id}/`);
	if (!draftRes.ok) {
		throw error(draftRes.status, 'Library draft not found');
	}
	const draft = await draftRes.json();

	const query = new URLSearchParams();
	const frameworkUrn = url.searchParams.get('framework_urn');
	if (frameworkUrn) query.set('framework_urn', frameworkUrn);
	const editorRes = await fetch(
		`${BASE_API_URL}/library-drafts/${params.id}/framework-editor/?${query}`
	);
	if (!editorRes.ok) {
		const detail = await editorRes.json().catch(() => ({}));
		throw error(editorRes.status, detail.error ?? 'No framework in this draft');
	}
	const editorData = await editorRes.json();

	return { draft, editorData };
};
