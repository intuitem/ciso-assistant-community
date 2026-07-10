import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, locals }) => {
	const [drafts, customLibraries] = await Promise.all([
		fetch(`${BASE_API_URL}/library-drafts/?ordering=-updated_at`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => []),
		// Adoption candidates: custom (non-builtin) stored libraries.
		fetch(`${BASE_API_URL}/stored-libraries/?is_custom=true&ordering=name`)
			.then((r) => r.json())
			.then((d) => d.results ?? d)
			.catch(() => [])
	]);

	return {
		drafts,
		customLibraries,
		// Instance-wide authoring identity (general settings); the last
		// packager typed in this browser overrides it in the forms.
		defaultPackager: locals.settings?.default_packager ?? 'custom'
	};
}) satisfies PageServerLoad;
