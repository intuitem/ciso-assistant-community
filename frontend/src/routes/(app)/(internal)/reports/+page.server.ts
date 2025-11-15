import type { PageServerLoad } from './$types';
import { m } from '$paraglide/messages';

export const load: PageServerLoad = async ({ locals }) => {
	return {
		user: locals.user,
		title: m.reports()
	};
};
