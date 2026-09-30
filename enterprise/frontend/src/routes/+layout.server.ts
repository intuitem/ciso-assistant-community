import type { LayoutServerLoad } from './$types';
import type { GlobalSettings } from '$lib/utils/types';
import { BASE_API_URL } from '$lib/utils/constants';

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
			favicon: '',
			logo_hash: '',
			favicon_hash: ''
		}
	};
}

async function fetchOrgTree(fetch: Parameters<LayoutServerLoad>[0]['fetch']) {
	try {
		const res = await fetch(
			`${BASE_API_URL}/folders/org_tree/?include_perimeters=false&no_focus=true`
		);
		if (res.ok) {
			return await res.json();
		}
	} catch (e) {
		console.error('Failed to fetch folder tree for focus mode:', e);
	}
	return null;
}

async function fetchLicenseStatus(fetch: Parameters<LayoutServerLoad>[0]['fetch']) {
	try {
		const res = await fetch(`${BASE_API_URL}/license-status/`);
		if (res.ok) {
			return await res.json();
		}
		console.error('Failed to fetch license status:', res.status, res.statusText);
	} catch (e) {
		console.error('Error fetching license status:', e);
	}
	return {};
}

export const load: LayoutServerLoad = async ({ fetch, locals, url, untrack }) => {
	const isSSOAuthenticate = untrack(() => url.pathname.startsWith('/sso/authenticate'));
	const clientSettings = isSSOAuthenticate
		? {
				name: 'clientSettings',
				settings: {
					name: '',
					logo: '',
					favicon: '',
					show_images_unauthenticated: false
				}
			}
		: await fetchClientSettings(fetch);
	const user = await locals.getUser();
	const focusModeEnabled = user ? ((await locals.getFeatureFlags())?.focus_mode ?? false) : false;
	const [orgTree, licenseStatus] = await Promise.all([
		focusModeEnabled ? fetchOrgTree(fetch) : null,
		user ? fetchLicenseStatus(fetch) : {}
	]);
	return {
		featureFlags: locals.featureFlags,
		clientSettings: sanitizeClientSettings(clientSettings, Boolean(user)),
		orgTree,
		licenseStatus
	};
};
