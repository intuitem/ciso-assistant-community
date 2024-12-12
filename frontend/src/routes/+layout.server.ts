import type { LayoutServerLoad } from './$types';
import { setLanguageTag } from '$paraglide/runtime';
import { DEFAULT_LANGUAGE } from '$lib/utils/constants';

export const load: LayoutServerLoad = async ({ locals, cookies }) => {
	setLanguageTag(cookies.get('ciso_lang') || DEFAULT_LANGUAGE);
	return { featureFlags: locals.featureFlags };
};
