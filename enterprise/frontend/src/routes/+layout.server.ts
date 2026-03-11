import type { LayoutServerLoad } from './$types';
import type { GlobalSettings } from '$lib/utils/types';
import { BASE_API_URL } from '$lib/utils/constants';
import { env } from '$env/dynamic/public';

export const load: LayoutServerLoad = async ({ fetch, locals }) => {
	let clientSettings: GlobalSettings;
	if (!locals.globalSettings) {
		let _settings = {};
		try {
			const res = await fetch('/settings/client-settings');
			if (res.ok) {
				_settings = await res.json();
			} else {
				console.error('Failed to fetch client settings:', res.status, res.statusText);
			}
		} catch (e) {
			console.error('Error fetching client settings:', e);
		}
		clientSettings = { name: 'clientSettings', settings: _settings };
	} else clientSettings = locals.globalSettings;

	if (!locals.user && clientSettings.settings.show_images_unauthenticated !== true) {
		clientSettings.settings.logo = '';
		clientSettings.settings.favicon = '';
		clientSettings.settings.logo_hash = '';
		clientSettings.settings.favicon_hash = '';
		clientSettings.settings.name = '';
	}

	return {
		featureFlags: locals.featureFlags,
		clientSettings
	};
};
