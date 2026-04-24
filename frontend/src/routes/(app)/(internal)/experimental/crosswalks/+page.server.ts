import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	const [crosswalksRes, frameworksRes, librarySourcesRes] = await Promise.all([
		fetch(`${BASE_API_URL}/crosswalks/`),
		fetch(`${BASE_API_URL}/frameworks/?ordering=name&page_size=1000`),
		fetch(`${BASE_API_URL}/crosswalks/library-sources/`)
	]);

	const crosswalksData = crosswalksRes.ok ? await crosswalksRes.json() : {};
	const frameworksData = frameworksRes.ok ? await frameworksRes.json() : {};
	const librarySources = librarySourcesRes.ok ? await librarySourcesRes.json() : [];

	const crosswalks = crosswalksData.results ?? crosswalksData ?? [];
	const frameworks = frameworksData.results ?? frameworksData ?? [];

	return { crosswalks, frameworks, librarySources };
}) satisfies PageServerLoad;
