import { BASE_API_URL } from '#lib/utils/constants.js';
import { m } from '#paraglide/messages.js';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const PROCESSINGS_ENDPOINT = `${BASE_API_URL}/privacy/processings/`;

export const load: PageServerLoad = async ({ fetch, url }) => {
	// The filter, search and page travel in the page's own URL.
	const query = new URLSearchParams();
	for (const key of ['state', 'search', 'offset']) {
		const value = url.searchParams.get(key);
		if (value) query.set(key, value);
	}
	const [res, formsRes] = await Promise.all([
		fetch(`${PROCESSINGS_ENDPOINT}dpia-overview/?${query}`),
		fetch(`${PROCESSINGS_ENDPOINT}dpia-screening-forms/`)
	]);
	if (!res.ok) {
		error(res.status, 'Error loading the DPIA overview');
	}
	return {
		overview: await res.json(),
		forms: formsRes.ok ? await formsRes.json() : [],
		title: m.dpias()
	};
};
