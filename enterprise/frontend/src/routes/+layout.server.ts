import type { LayoutServerLoad } from './$types';
import type { GlobalSettings } from '$lib/utils/types';

export const load: LayoutServerLoad = async ({ fetch, locals }) => {
	let clientSettings: GlobalSettings;
	if (!locals.globalSettings) {
		const _settings = await fetch('/settings/client-settings').then((res) => res.json());
		clientSettings = { name: 'clientSettings', settings: _settings };
	} else clientSettings = locals.globalSettings;
  if (!locals.user && clientSettings.settings.show_images_unauthenticated !== true) {
    clientSettings.settings.logo = '';
    clientSettings.settings.favicon = '';
    clientSettings.settings.logo_hash = '';
    clientSettings.settings.favicon_hash = '';
  }
	return { featureFlags: locals.featureFlags, clientSettings };
};
