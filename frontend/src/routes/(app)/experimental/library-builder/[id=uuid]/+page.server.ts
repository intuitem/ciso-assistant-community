import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params }) => {
	const draftRes = await fetch(`${BASE_API_URL}/library-drafts/${params.id}/`);
	if (!draftRes.ok) {
		throw error(draftRes.status, 'Library draft not found');
	}
	const draft = await draftRes.json();

	// Import sources: every stored library (clone works from builtin too),
	// plus other drafts (a draft is a library document you can borrow from
	// without publishing it first).
	const [storedLibraries, drafts] = await Promise.all([
		fetchAllPages(fetch, `${BASE_API_URL}/stored-libraries/?ordering=name`).catch(() => []),
		fetchAllPages<{ id: string }>(fetch, `${BASE_API_URL}/library-drafts/?ordering=name`).catch(
			() => [] as { id: string }[]
		)
	]);
	const otherDrafts = (drafts ?? []).filter((d: { id: string }) => d.id !== params.id);

	return { draft, storedLibraries, otherDrafts };
};
