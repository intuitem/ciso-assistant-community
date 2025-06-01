import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load = (async () => {
	return { title: m.auditLog() };
}) satisfies PageServerLoad;
