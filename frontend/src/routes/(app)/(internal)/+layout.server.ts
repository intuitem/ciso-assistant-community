import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';

export const load = loadFlash(async ({ locals }) => {
	if (locals.user.is_third_party) {
        redirect(302, `/compliance-assessments`);
    }
	return { user: locals.user };
}) satisfies LayoutServerLoad;