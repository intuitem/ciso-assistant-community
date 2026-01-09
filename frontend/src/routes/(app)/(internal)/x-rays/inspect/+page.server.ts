import { BASE_API_URL } from '$lib/utils/constants';
import { m } from '$paraglide/messages';
import type { PageServerLoad } from './$types';

export const load = (async ({ fetch, url }) => {
	const includeEnclaves = url.searchParams.get('include_enclaves') ?? 'false';
	const endpoint = `${BASE_API_URL}/folders/org_tree/?include_enclaves=${includeEnclaves}`;

	const res = await fetch(endpoint);
	const data = await res.json();

	return { data, title: m.inspect(), includeEnclaves: includeEnclaves === 'true' };
}) satisfies PageServerLoad;
