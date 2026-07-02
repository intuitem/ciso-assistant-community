import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// A document container's "detail" is its rich editor — send viewers straight there.
export const load: PageServerLoad = async ({ params }) => {
	redirect(302, `/document-containers/${params.id}/document`);
};
