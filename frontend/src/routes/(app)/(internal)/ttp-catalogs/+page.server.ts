import { BASE_API_URL } from '#lib/utils/constants.js';
import { fetchAllPages } from '#lib/utils/pagination.js';
import { logger } from '#lib/server/logger.js';
import { error } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const catalogs = await fetchAllPages(fetch, `${BASE_API_URL}/ttp-catalogs/`).catch((e) => {
		// The message names the backend URL: log it, never return it
		logger.error('Failed to load TTP catalogs', { error: e });
		error(e.status ?? 500, 'Could not load the TTP catalogs');
	});

	return { catalogs };
};
