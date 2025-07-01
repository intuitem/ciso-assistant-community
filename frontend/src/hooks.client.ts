import { page } from '$app/state';
import { defineCustomClientStrategy } from '$paraglide/runtime';

defineCustomClientStrategy('custom-userPreference', {
	getLocale: () => {
		return page?.data?.user?.preferences?.lang;
	},
	setLocale: async (locale) => {
		console.log('Setting locale to:', locale);
	}
});
