import { writable, type Writable, get } from 'svelte/store';
import { getContext, setContext } from 'svelte';

/**
 * A persisted writable store of collapsed node IDs, backed by localStorage.
 * One framework + one "view" (cards vs ToC) gets one store instance.
 */
export interface CollapsedStore {
	subscribe: Writable<Set<string>>['subscribe'];
	has: (nodeId: string) => boolean;
	toggle: (nodeId: string) => void;
	collapse: (nodeId: string) => void;
	expand: (nodeId: string) => void;
	collapseAll: (nodeIds: string[]) => void;
	expandAll: () => void;
}

export function createCollapsedStore(storageKey: string): CollapsedStore {
	// Load initial state from localStorage
	let initial: Set<string> = new Set();
	if (typeof localStorage !== 'undefined') {
		try {
			const raw = localStorage.getItem(storageKey);
			if (raw) initial = new Set(JSON.parse(raw) as string[]);
		} catch {
			// Ignore — start empty if anything fails (corrupt JSON, quota, etc.)
		}
	}

	const store = writable<Set<string>>(initial);

	function persist(next: Set<string>) {
		if (typeof localStorage === 'undefined') return;
		try {
			localStorage.setItem(storageKey, JSON.stringify([...next]));
		} catch {
			// Quota exceeded or disabled — just skip persistence
		}
	}

	function update(mutator: (s: Set<string>) => void) {
		store.update((s) => {
			const next = new Set(s);
			mutator(next);
			persist(next);
			return next;
		});
	}

	return {
		subscribe: store.subscribe,
		has: (nodeId) => get(store).has(nodeId),
		toggle: (nodeId) =>
			update((s) => {
				if (s.has(nodeId)) s.delete(nodeId);
				else s.add(nodeId);
			}),
		collapse: (nodeId) => update((s) => s.add(nodeId)),
		expand: (nodeId) => update((s) => s.delete(nodeId)),
		collapseAll: (nodeIds) =>
			update((s) => {
				for (const id of nodeIds) s.add(id);
			}),
		expandAll: () => {
			store.set(new Set());
			persist(new Set());
		}
	};
}

const CARD_COLLAPSED_KEY = Symbol('card-collapsed');

export function setCardCollapsedContext(store: CollapsedStore) {
	setContext(CARD_COLLAPSED_KEY, store);
}

export function getCardCollapsedContext(): CollapsedStore {
	return getContext(CARD_COLLAPSED_KEY);
}
