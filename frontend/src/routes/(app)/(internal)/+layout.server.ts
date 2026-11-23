import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';
import { loadFlash } from 'sveltekit-flash-message/server';

export const load = loadFlash(async ({ locals, route, untrack }) => {
	const user = await locals.getUser();
	if (user?.is_third_party) {
		// A task link, as the assignment email carries, leads to the vendor's own tasks.
		// Untracked: reading route.id would re-run this load on every navigation.
		if (untrack(() => route.id) === '/(app)/(internal)/task-templates/[id=uuid]') {
			redirect(302, `/my-tasks?mine`);
		}
		redirect(302, `/auditee-dashboard`);
	}
	return { user };
}) satisfies LayoutServerLoad;
