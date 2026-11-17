import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';

export const load = loadFlash(async ({ locals }) => {
	const user = await locals.getUser();
	if (user?.is_third_party) {
		redirect(302, `/auditee-dashboard`);
	}
	return { user };
}) satisfies LayoutServerLoad;
