import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	// Domains (DO) and the global root (GL) are the valid evidence containers,
	// matching what FolderTreeSelect surfaces by default.
	const res = await fetch(
		`${BASE_API_URL}/folders/?content_type=DO&content_type=GL&page_size=1000`
	);
	const data = await res.json();
	const folders = data.results || data || [];
	return { folders };
}) satisfies PageServerLoad;
