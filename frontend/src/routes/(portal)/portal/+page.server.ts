import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { portals } = await parent();
	if (portals?.length) {
		redirect(302, `/portal/${portals[0].id}`);
	}
	return {};
};
