// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
// and what to do when importing types

import type { User } from '#lib/utils/types.js';
import type { FeatureFlags } from '#lib/feature-flags.js';

declare global {
	namespace App {
		interface Error {
			message: string;
			status: number;
			// Backend error fields (detail, error, ...) relayed to the client by errorFromBody
			[key: string]: unknown;
		}
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
