// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
// and what to do when importing types

import type { User, GlobalSettings } from '$lib/utils/types';
import type { FeatureFlags } from '$lib/feature-flags';

declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			user: User;
			featureFlags: FeatureFlags;
			globalSettings: GlobalSettings;
		}
		interface PageData {
			flash?: { type: 'success' | 'error' | 'warning' | 'info'; message: string };
		}
		// interface Platform {}
	}
}

export {};
