import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
	const endpoint = `/stored-libraries/${params.id}`;
	const queryParams = url.searchParams.toString();
	const library = await fetch(`${endpoint}?${queryParams}`).then((res) => res.json());

	return {
		tree: fetch(`${endpoint}/tree?${queryParams}`)
			.then((res) => {
				if (!res.ok) throw new Error(`Failed to fetch tree: ${res.status}`);
				return res.json();
			})
			.catch((error) => {
				console.error('Error fetching tree:', error);
				return {};
			}),
		library
	};
};
