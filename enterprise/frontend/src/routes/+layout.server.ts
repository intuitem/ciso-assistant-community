import type { LayoutServerLoad } from './$types';
import type { GlobalSettings } from '$lib/utils/types';

async function fetchClientSettings(
	fetch: Parameters<LayoutServerLoad>[0]['fetch']
): Promise<GlobalSettings> {
	try {
		const response = await fetch('/settings/client-settings');
		if (!response.ok) {
			console.error('Failed to fetch client settings:', response.status, response.statusText);
			return {
				name: 'clientSettings',
				settings: {
					name: '',
					logo: '',
					favicon: '',
					show_images_unauthenticated: false
				}
			};
		}
		const settings = await response.json();
		return { name: 'clientSettings', settings };
	} catch (error) {
		console.error('Error fetching client settings:', error);
		return {
			name: 'clientSettings',
			settings: {
				name: '',
				logo: '',
				favicon: '',
				show_images_unauthenticated: false
			}
		};
	}
}

function sanitizeClientSettings(
	clientSettings: GlobalSettings,
	isAuthenticated: boolean
): GlobalSettings {
	if (isAuthenticated || clientSettings.settings.show_images_unauthenticated === true) {
		return clientSettings;
	}
	return {
		...clientSettings,
		settings: {
			...clientSettings.settings,
			name: '',
			logo: '',
			favicon: ''
		}
	};
}

export const load: LayoutServerLoad = async ({ fetch, locals, url }) => {
	const isSSOAuthenticate = url.pathname.startsWith('/sso/authenticate');
	const clientSettings =
		locals.globalSettings ??
		(isSSOAuthenticate
			? {
					name: 'clientSettings',
					settings: {
						name: '',
						logo: '',
						favicon: '',
						show_images_unauthenticated: false
					}
				}
			: await fetchClientSettings(fetch));
	return {
		featureFlags: locals.featureFlags,
		generalSettings: locals.generalSettings,
		clientSettings: sanitizeClientSettings(clientSettings, Boolean(locals.user))
	};
};
