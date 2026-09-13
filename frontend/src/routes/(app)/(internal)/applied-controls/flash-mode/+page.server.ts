import { BASE_API_URL } from '$lib/utils/constants';
import { getSecureRedirect } from '$lib/utils/helpers';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';

// Flash mode shows one card at a time, so it loads one page and fetches the
// rest as the user advances. Loading the whole collection up front cost one
// request per 200 rows before the first card could render.
const PAGE_SIZE = 200;

export const load = (async ({ fetch, url }) => {
	const URLModel = 'applied-controls';
	const endpoint = `${BASE_API_URL}/${URLModel}/`;

	// Build query parameters based on the user's access (viewable objects pattern)
	const queryParams = new URLSearchParams();

	// Get search parameters from the URL to preserve any filters
	const searchParams = url.searchParams;
	for (const [key, value] of searchParams.entries()) {
		// Don't pass through UI-specific parameters to the API, nor paging
		// params: the page size is ours and a stray offset would shift every
		// index away from the row it names.
		if (!['backUrl', 'backLabel', 'limit', 'offset'].includes(key)) {
			queryParams.append(key, value);
		}
	}
	const filterQuery = queryParams.toString();

	const firstPageParams = new URLSearchParams(filterQuery);
	firstPageParams.set('offset', '0');
	firstPageParams.set('limit', String(PAGE_SIZE));

	const response = await fetch(`${endpoint}?${firstPageParams.toString()}`);
	if (!response.ok) {
		console.error('Failed to load applied controls:', response.status);
	}
	const firstPage = response.ok ? await response.json() : { results: [], count: 0 };

	// Extract UI parameters for the flash mode page
	const backUrl = getSecureRedirect(searchParams.get('backUrl')) || '/applied-controls';
	const backLabel = searchParams.get('backLabel') || 'Applied Controls';

	return {
		URLModel,
		applied_controls: firstPage.results ?? [],
		count: firstPage.count ?? 0,
		filterQuery,
		pageSize: PAGE_SIZE,
		backUrl,
		backLabel
	};
}) satisfies PageServerLoad;

export const actions: Actions = {
	updateAppliedControl: async (event) => {
		const data = await event.request.json();
		const value: {
			id: string;
			status?: string;
			effort?: string;
			priority?: string;
			control_impact?: string;
			csf_function?: string;
		} = data;

		const URLModel = 'applied-controls';
		const endpoint = `${BASE_API_URL}/${URLModel}/${value.id}/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			body: JSON.stringify(value)
		};

		const res = await event.fetch(endpoint, requestInitOptions);
		return { status: res.status, body: await res.json() };
	}
};
