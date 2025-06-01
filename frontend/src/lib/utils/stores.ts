import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { persisted } from 'svelte-persisted-store';
import type { TreeViewNode } from '@skeletonlabs/skeleton';
import type { Driver } from 'driver.js';

export const showNotification = writable(
	(browser && localStorage.getItem('showNotification')) || 'false'
);
showNotification.subscribe((val) => {
	if (browser) return (localStorage.showNotification = val);
});

export const pageTitle = writable('');
export const clientSideToast = writable(undefined);

const requirementAssessmentsList: string[] = [];

export const hideSuggestions = persisted('hideSuggestions', requirementAssessmentsList, {
	storage: 'session'
});

export const showAllEvents = persisted('showAllEvents', true, {
	storage: 'session'
});

export const lastAccordionItem = persisted('lastAccordionItem', '');

const expandedNodes: TreeViewNode[] = [];

export const expandedNodesState = persisted('expandedNodes', expandedNodes, {
	storage: 'session'
});

export const createModalCache = {
	_urlModel: '',
	_cacheToDelete: new Set(),
	deleteCache(cacheName: any) {
		this._cacheToDelete.add(cacheName);
	},
	garbageCollect() {
		for (const cacheName of this._cacheToDelete) {
			delete this.data[cacheName];
		}
		this._cacheToDelete.clear();
	},
	clear() {
		for (const cacheName of Object.keys(this.data)) {
			delete this.data[cacheName];
		}
	},
	setModelName(urlModelFromPage: string) {
		if (this._urlModel !== urlModelFromPage) this.clear();
		this._urlModel = urlModelFromPage;
	},
	data: {}
};

export const driverInstance = writable<Driver | null>(null);

function createPersistedAuditFilters() {
	const stored = browser ? localStorage.getItem('auditFilters') : null;
	const initial = stored ? JSON.parse(stored) : {};

	const { subscribe, set, update } = writable(initial);

	if (browser) {
		subscribe((value) => {
			localStorage.setItem('auditFilters', JSON.stringify(value));
		});
	}

	return {
		subscribe,
		set,
		update,
		setStatus(id, statusArray) {
			update((filters) => {
				if (!filters[id]) filters[id] = {};
				filters[id].selectedStatus = statusArray;
				return filters;
			});
		},
		setResults(id, resultsArray) {
			update((filters) => {
				if (!filters[id]) filters[id] = {};
				filters[id].selectedResults = resultsArray;
				return filters;
			});
		},
		setDisplayOnlyAssessableNodes(id, displayOnlyAssessableNodes) {
			update((filters) => {
				if (!filters[id]) filters[id] = {};
				filters[id].displayOnlyAssessableNodes = displayOnlyAssessableNodes;
				return filters;
			});
		}
	};
}

export const auditFiltersStore = createPersistedAuditFilters();
