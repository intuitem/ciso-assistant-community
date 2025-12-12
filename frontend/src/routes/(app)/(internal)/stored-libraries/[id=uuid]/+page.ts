import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
	let endpoint = `/stored-libraries/${params.id}`;
	const queryParams = url.searchParams.toString();
	let library = await fetch(`${endpoint}?${queryParams}`).then((res) => res.json());

	const isExclusivelyLoaded = !library.builtin && Object.keys(library.objects).length === 0;

	if (isExclusivelyLoaded) {
		const loadedLibraryId = library.loaded_library;

		if (loadedLibraryId !== null) {
			endpoint = `/loaded-libraries/${loadedLibraryId}`;
			library = await fetch(`${endpoint}?${queryParams}`).then((res) => res.json());
		} else {
			console.error('Loaded library id not found.');
		}
	}

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
		library,
		title: library.name
	};
};
