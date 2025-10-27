import { writable, get } from 'svelte/store';

/**
 * Global cache for attachment blob URLs
 * Prevents duplicate downloads of the same evidence attachment
 */

interface CachedAttachment {
	type: string;
	url: string;
	fileExists: boolean;
}

interface AttachmentCache {
	[key: string]: CachedAttachment;
}

function createAttachmentCache() {
	const { subscribe, set, update } = writable<AttachmentCache>({});

	return {
		subscribe,
		/**
		 * Get a cached attachment by key
		 */
		get: (key: string): CachedAttachment | undefined => {
			const cache = get({ subscribe });
			return cache[key];
		},
		/**
		 * Store an attachment in the cache
		 */
		set: (key: string, value: CachedAttachment) => {
			update((cache) => {
				cache[key] = value;
				return cache;
			});
		},
		/**
		 * Remove an attachment from the cache and revoke its blob URL
		 */
		remove: (key: string) => {
			update((cache) => {
				if (cache[key]) {
					URL.revokeObjectURL(cache[key].url);
					delete cache[key];
				}
				return cache;
			});
		},
		/**
		 * Clear all cached attachments and revoke all blob URLs
		 */
		clear: () => {
			update((cache) => {
				Object.values(cache).forEach((attachment) => {
					URL.revokeObjectURL(attachment.url);
				});
				return {};
			});
		},
		/**
		 * Check if an attachment is in the cache
		 */
		has: (key: string): boolean => {
			const cache = get({ subscribe });
			return key in cache;
		}
	};
}

export const attachmentCache = createAttachmentCache();

/**
 * Generate a cache key for an attachment
 */
export function generateAttachmentCacheKey(id: string, attachmentName: string): string {
	return `${id}-${attachmentName}`;
}
