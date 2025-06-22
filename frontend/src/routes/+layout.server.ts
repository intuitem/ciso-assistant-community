import type { LayoutServerLoad } from './$types';
import { setLocale } from '$paraglide/runtime';
import { DEFAULT_LANGUAGE } from '$lib/utils/constants';

export const load: LayoutServerLoad = async ({ locals, cookies }) => {
	setLocale(cookies.get('PARAGLIDE_LOCALE') || DEFAULT_LANGUAGE);
	return { featureFlags: locals.featureFlags };
};
