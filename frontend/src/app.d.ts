// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
// and what to do when importing types

import type { User } from '$lib/utils/types';
import type { FeatureFlags } from '$lib/feature-flags';

declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			// Populated as a side effect of the accessors below; only set once
			// something has actually asked for them. Read these directly only
			// after awaiting the matching accessor in the same request.
			user: User;
			settings: Record<string, any>;
			featureflags: Record<string, boolean>;
			// Memoised per request: the first call fetches, the rest reuse it.
			getUser: () => Promise<User | null>;
			getSettings: () => Promise<Record<string, any> | undefined>;
			getFeatureFlags: () => Promise<Record<string, boolean> | undefined>;
			// Static catalogue of flag names, not their values — no round-trip.
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
