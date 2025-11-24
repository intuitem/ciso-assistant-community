import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

export const load: LayoutServerLoad = async ({ locals }) => {
	console.log(locals?.featureflags?.outgoing_webhooks);
	if (!locals?.featureflags?.outgoing_webhooks) {
		redirect(302, '/settings');
	}

	return {};
};
