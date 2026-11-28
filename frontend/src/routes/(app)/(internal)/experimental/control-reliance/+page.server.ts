import { BASE_API_URL } from '#lib/utils/constants.js';
import type { PageServerLoad } from './$types';
import type { Portfolio } from './reliance';

export const load: PageServerLoad = async ({ fetch }) => {
	const response = await fetch(`${BASE_API_URL}/applied-controls/reliance/`).catch(() => null);
	return {
		portfolio: response?.ok ? ((await response.json()) as Portfolio) : null,
		denied: response?.status === 401 || response?.status === 403,
		title: 'Control reliance'
	};
};
