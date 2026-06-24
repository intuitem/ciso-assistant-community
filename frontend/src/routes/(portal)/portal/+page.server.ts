import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ parent }) => {
	const { portals } = await parent();
	if (portals?.length) {
		const target = portals.find((p) => p.is_default) ?? portals[0];
		redirect(302, `/portal/${target.id}`);
	}
	return {};
};
