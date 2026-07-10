import { BASE_API_URL } from '$lib/utils/constants';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const presets = await fetch(`${BASE_API_URL}/presets/?ordering=-updated_at`)
		.then((r) => r.json())
		.then((d) => d.results ?? d)
		.catch(() => []);

	const userAuthored = presets.filter((p: any) => p.is_user_authored);
	const libraryPresets = presets.filter((p: any) => !p.is_user_authored);

	return { userAuthored, libraryPresets };
};
