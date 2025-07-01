import { page } from '$app/state';
import { DEFAULT_LANGUAGE } from '$lib/utils/constants';
import { defineCustomClientStrategy } from '$paraglide/runtime';

defineCustomClientStrategy('custom-userPreference', {
	getLocale: () => {
		return page?.data?.user?.preferences?.lang || DEFAULT_LANGUAGE;
	},
	/**
	 * NOTE: setLocale is delegated to paraglide's cookie strategy
	 */
	setLocale: async () => {}
});
