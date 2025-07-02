import { page } from '$app/state';
import { DEFAULT_LANGUAGE } from '$lib/utils/constants';
import { defineCustomClientStrategy } from '$paraglide/runtime';

defineCustomClientStrategy('custom-userPreference', {
	getLocale: () => {
		return page?.data?.user?.preferences?.lang;
	},
	/**
	 * NOTE: setLocale is delegated to paraglide's cookie strategy
	 */
	setLocale: async () => {}
});

defineCustomClientStrategy('custom-fallback', {
	getLocale: () => {
		return DEFAULT_LANGUAGE;
	},
	setLocale: async () => {}
});
