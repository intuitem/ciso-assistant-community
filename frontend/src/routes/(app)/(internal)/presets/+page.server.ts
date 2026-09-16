import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const presetsPromise = fetchAllPages(fetch, `${BASE_API_URL}/presets/`).catch(() => []);

	const journeysPromise = fetch(`${BASE_API_URL}/journeys/?ordering=-updated_at&limit=10`)
		.then((res) => res.json())
		.then((data) => data.results ?? data)
		.catch(() => []);

	const domainsPromise = fetchAllPages(
		fetch,
		`${BASE_API_URL}/folders?content_type=DO&content_type=GL`
	).catch(() => []);

	const [presets, journeys, domains] = await Promise.all([
		presetsPromise,
		journeysPromise,
		domainsPromise
	]);

	return {
		presets,
		journeys,
		domains,
		title: 'presets',
		modelDescriptionKey: 'presetsDescription'
	};
};
