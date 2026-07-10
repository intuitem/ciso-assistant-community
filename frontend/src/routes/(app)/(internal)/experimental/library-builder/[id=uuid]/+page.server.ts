import { BASE_API_URL } from '$lib/utils/constants';
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
		fetch(`${BASE_API_URL}/stored-libraries/?ordering=name`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => []),
		fetch(`${BASE_API_URL}/library-drafts/?ordering=name`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => [])
	]);
	const otherDrafts = (drafts ?? []).filter((d: { id: string }) => d.id !== params.id);

	return { draft, storedLibraries, otherDrafts };
};
