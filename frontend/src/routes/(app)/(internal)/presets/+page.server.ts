import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const presetsPromise = fetch(`${BASE_API_URL}/stored-libraries/?is_preset=true`)
		.then((res) => res.json())
		.then((data) => data.results ?? data)
		.catch(() => []);

	const journeysPromise = fetch(`${BASE_API_URL}/preset-journeys/`)
		.then((res) => res.json())
		.then((data) => data.results ?? data)
		.catch(() => []);

	const domainsPromise = fetch(`${BASE_API_URL}/folders?content_type=DO&content_type=GL`)
		.then((res) => res.json())
		.then((data) => data.results ?? data)
		.catch(() => []);

	const [presets, journeys, domains] = await Promise.all([
		presetsPromise,
		journeysPromise,
		domainsPromise
	]);

	return {
		presets,
		journeys,
		domains,
		title: 'presets'
	};
};
