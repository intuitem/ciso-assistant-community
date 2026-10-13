// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
// and what to do when importing types

import type { User } from '$lib/utils/types';
import type { FeatureFlags } from '$lib/feature-flags';

declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			// Set by the accessors below; only valid after awaiting the matching one.
			user?: User;
			settings?: Record<string, any>;
			featureflags?: Record<string, boolean>;
			getUser: () => Promise<User | null>;
			getSettings: () => Promise<Record<string, any> | undefined>;
			getFeatureFlags: () => Promise<Record<string, boolean> | undefined>;
			// Flag names, not their values — unrelated to `featureflags` above.
			featureFlags: FeatureFlags;
		}
		interface PageData {
			flash?: {
				type: 'success' | 'error' | 'warning' | 'info';
				message: string;
				timeout?: number;
				autohide?: boolean;
			};
		}
		// interface Platform {}
	}
}

export {};
