import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import type { Actions } from '@sveltejs/kit';

export const load = (async ({ fetch, url }) => {
	const URLModel = 'applied-controls';
	const endpoint = `${BASE_API_URL}/${URLModel}/`;

	// Build query parameters based on the user's access (viewable objects pattern)
	const queryParams = new URLSearchParams();

	// Get search parameters from the URL to preserve any filters
	const searchParams = url.searchParams;
	for (const [key, value] of searchParams.entries()) {
		queryParams.set(key, value);
	}

	const fullEndpoint = `${endpoint}?${queryParams.toString()}`;
	const response = await fetch(fullEndpoint);
	const appliedControlsData = await response.json();

	return {
		URLModel,
		applied_controls: appliedControlsData.results || appliedControlsData
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
