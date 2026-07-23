import { BASE_API_URL } from '$lib/utils/constants';
import { fetchAllPages } from '$lib/utils/pagination';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch }) => {
	// Domains (DO) and the global root (GL) are the valid evidence containers,
	// matching what FolderTreeSelect surfaces by default.
	const folders = await fetchAllPages(
		fetch,
		`${BASE_API_URL}/folders/?content_type=DO&content_type=GL`
	).catch(() => []);
	return { folders };
}) satisfies PageServerLoad;
