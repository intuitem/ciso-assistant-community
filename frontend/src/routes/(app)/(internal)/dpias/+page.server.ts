import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => ({ title: m.dpias() });
