import { redirect } from '@sveltejs/kit';

import type { PageServerLoad } from './$types';

export const load = (async () => {
	const today = new Date();
	const currentMonth = today.getMonth() + 1;
	const currentYear = today.getFullYear();
	redirect(302, `/calendar/${currentYear}/${currentMonth}`);
}) satisfies PageServerLoad;
