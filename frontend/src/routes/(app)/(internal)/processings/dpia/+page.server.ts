import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

const PROCESSINGS_ENDPOINT = `${BASE_API_URL}/privacy/processings/`;

export const load: PageServerLoad = async ({ fetch }) => {
	const [res, formsRes] = await Promise.all([
		fetch(`${PROCESSINGS_ENDPOINT}dpia-overview/`),
		fetch(`${PROCESSINGS_ENDPOINT}dpia-screening-forms/`)
	]);
	if (!res.ok) {
		error(res.status, 'Error loading the DPIA overview');
	}
	return {
		overview: await res.json(),
		forms: formsRes.ok ? await formsRes.json() : [],
		title: m.dpiaStatusOverview()
	};
};
