/**
 * Shared reference catalog for node → threat / reference-control links.
 *
 * Fetched once per editor mount from the `_action` protocol host and shared
 * through context so every ReferentialLinks instance resolves labels and
 * picks from the same data. Hosts that do not implement the
 * `reference-catalog` action (no library draft behind them) leave the store
 * in the `error` state and the links UI stays hidden.
 */
import { getContext, setContext } from 'svelte';
import { writable, type Writable } from 'svelte/store';
import { browser } from '$app/environment';
import { apiReferenceCatalog, type ReferentialCatalog } from './builder-api';

export interface ReferentialCatalogState {
	status: 'loading' | 'ready' | 'error';
	catalog: ReferentialCatalog | null;
}

export type ReferentialCatalogStore = Writable<ReferentialCatalogState>;

const CONTEXT_KEY = 'framework-builder-referential-catalog';

export function initReferentialCatalog(apiTarget: string): ReferentialCatalogStore {
	const store = writable<ReferentialCatalogState>({ status: 'loading', catalog: null });
	if (browser) {
		apiReferenceCatalog(apiTarget)
			.then((catalog) => store.set({ status: 'ready', catalog }))
			.catch(() => store.set({ status: 'error', catalog: null }));
	}
	setContext(CONTEXT_KEY, store);
	return store;
}

export function getReferentialCatalog(): ReferentialCatalogStore | undefined {
	return getContext(CONTEXT_KEY);
}
