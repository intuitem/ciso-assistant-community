// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
// and what to do when importing types

import type { User } from '$lib/utils/types';

declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			user: User;
		}
		interface PageData {
			flash?: { type: 'success' | 'error' | 'warning' | 'info'; message: string };
		}
		// interface Platform {}
	}
}

export {};
