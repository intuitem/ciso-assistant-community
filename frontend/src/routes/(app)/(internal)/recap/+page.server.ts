import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async ({ locals, fetch }) => {
	// /recap used to trigger a request cascade:
	// folders -> assessments per folder -> donut/global_score per assessment.
	// The dedicated backend endpoint returns the exact shape needed by the page
	// in one call, which removes the previous N+1 pattern from the frontend.
	const folders = await fetch(`${BASE_API_URL}/compliance-assessments/recap/`)
		.then(async (res) => {
			if (!res.ok) {
				throw new Error(`Failed to load recap data: ${res.status} ${res.statusText}`);
			}
			return res.json();
		})
		.then((data) => data.results ?? [])
		.catch((error) => {
			// Keep the page renderable even if the recap endpoint fails temporarily.
			console.error('Failed to load recap:', error);
			return [];
		});

	return {
		folders,
		user: locals.user,
		title: m.recap()
	};
};
