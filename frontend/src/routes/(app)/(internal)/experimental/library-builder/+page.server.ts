import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, locals }) => {
	const [drafts, customLibraries, orphanFrameworks] = await Promise.all([
		fetchAllPages(fetch, `${BASE_API_URL}/library-drafts/?ordering=-updated_at`).catch(() => []),
		// Adoption candidates: custom (non-builtin) stored libraries.
		fetchAllPages(fetch, `${BASE_API_URL}/stored-libraries/?is_custom=true&ordering=name`).catch(
			() => []
		),
		// Adoption candidates: library-less live frameworks (retired editor).
		fetchAllPages(fetch, `${BASE_API_URL}/frameworks/?library__isnull=true&ordering=name`).catch(
			() => []
		)
	]);

	return {
		drafts,
		customLibraries,
		orphanFrameworks,
		// Instance-wide authoring identity (general settings); the last
		// packager typed in this browser overrides it in the forms.
		defaultPackager: locals.settings?.default_packager ?? 'custom'
	};
}) satisfies PageServerLoad;
