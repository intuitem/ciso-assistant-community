import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url, fetch }) => {
	const query = url.searchParams.get('q') || '';
	const type = url.searchParams.get('type') || '';

	if (!query.trim()) {
		return { query, results: [], count: 0, totalCandidates: 0 };
	}

	const params = new URLSearchParams({ q: query });
	if (type) params.set('type', type);

	const res = await fetch(`${BASE_API_URL}/search/?${params.toString()}`);
	if (!res.ok) {
		return { query, results: [], count: 0, totalCandidates: 0 };
	}

	const data = await res.json();
	return {
		query,
		results: data.results ?? [],
		count: data.count ?? 0,
		totalCandidates: data.total_candidates ?? 0
	};
};
