import { BASE_API_URL } from '$lib/utils/constants';
import { getSecureRedirect } from '$lib/utils/helpers';
import type { PageServerLoad } from './$types';
import { error, type Actions } from '@sveltejs/kit';

// Swimlane cards are fetched per folder as the user opens them. Below this many
// matching controls the whole board fits in one request, so it is loaded up
// front and every swimlane starts expanded: small boards behave as before.
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
		// params: the page size is ours to set per swimlane.
		if (!['backUrl', 'backLabel', 'limit', 'offset'].includes(key)) {
			queryParams.append(key, value);
		}
	}
	const filterQuery = queryParams.toString();

	// One aggregate query gives every swimlane and its true per-status totals, so
	// the board can render truthful headers without holding a card per row.
	const countsResponse = await fetch(`${endpoint}counts_per_folder/?${filterQuery}`);
	// Falling back to zero swimlanes here would render a failure as an empty board.
	if (!countsResponse.ok) {
		throw error(countsResponse.status, 'Failed to load kanban counts');
	}
	const counts = await countsResponse.json();

	let applied_controls: Record<string, any>[] = [];
	let preloaded = false;
	if (counts.total > 0 && counts.total <= PAGE_SIZE) {
		const params = new URLSearchParams(filterQuery);
		params.set('offset', '0');
		params.set('limit', String(PAGE_SIZE));
		const response = await fetch(`${endpoint}?${params.toString()}`);
		if (response.ok) {
			applied_controls = (await response.json()).results ?? [];
			preloaded = true;
		} else {
			console.error('Failed to load applied controls:', response.status);
		}
	}

	// Extract UI parameters for the kanban mode page
	const backUrl = getSecureRedirect(searchParams.get('backUrl')) || '/applied-controls';
	const backLabel = searchParams.get('backLabel') || 'Applied Controls';

	return {
		URLModel,
		applied_controls,
		counts,
		preloaded,
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
		} = data;

		const URLModel = 'applied-controls';
		const endpoint = `${BASE_API_URL}/${URLModel}/${value.id}/`;

		const requestInitOptions: RequestInit = {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(value)
		};

		const res = await event.fetch(endpoint, requestInitOptions);
		return { success: res.ok, status: res.status, body: await res.json() };
	}
};
