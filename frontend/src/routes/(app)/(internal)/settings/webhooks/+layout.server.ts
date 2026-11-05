import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

export const load: LayoutServerLoad = async ({ locals }) => {
	if (!(await locals.getFeatureFlags())?.outgoing_webhooks) {
		redirect(302, '/settings');
	}

	return {};
};
