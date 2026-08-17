import { error } from '@sveltejs/kit';
import { getHelpDocRaw, getHelpTitleBySlug } from '$lib/utils/helpContent';
import { renderHelpDoc } from '$lib/utils/helpMarkdown';

import type { PageServerLoad } from './$types';

export const load = (async ({ params }) => {
	const slug = params.slug ?? '';
	const raw = getHelpDocRaw(slug);
	if (raw === undefined) {
		error(404, 'Help page not found');
	}

	const { description, html } = renderHelpDoc(raw, slug);
	const title = getHelpTitleBySlug()[slug] ?? 'Documentation';

	return { title, description, html };
}) satisfies PageServerLoad;
