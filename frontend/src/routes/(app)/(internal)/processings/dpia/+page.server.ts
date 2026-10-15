import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// Merged into /dpias.
export const load: PageServerLoad = () => redirect(301, '/dpias');
