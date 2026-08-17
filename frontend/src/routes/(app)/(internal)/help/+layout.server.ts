import { getHelpNavTree } from '$lib/utils/helpContent';

import type { LayoutServerLoad } from './$types';

export const load = (async () => {
	return { navTree: getHelpNavTree() };
}) satisfies LayoutServerLoad;
