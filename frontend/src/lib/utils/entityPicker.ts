import EntityPickerModal from '$lib/components/Modals/EntityPickerModal.svelte';
import type { ModalComponent, ModalSettings, ModalStore } from '$lib/components/Modals/stores';

export interface EntityPickerColumn {
	key: string;
	label: string;
	filter?: 'icontains' | 'exact';
	sortable?: boolean;
}

export interface EntityPickerOptions {
	/** API resource whose `/{endpoint}/autocomplete` action backs the picker. */
	endpoint: string;
	title?: string;
	subtitle?: string;
	/** Object field used as the primary row label (default 'str'). */
	labelField?: string;
	/** Optional secondary text shown after the label (e.g. 'email'). */
	secondaryField?: string;
	/** Columns for the browse (table) mode. */
	columns?: EntityPickerColumn[];
	/** Fixed query params applied to every request (e.g. scoping filters). */
	scopeFilters?: Record<string, string>;
	/** Boolean field driving an active/inactive badge + an "include inactive" toggle. */
	activeField?: string;
	/** Seed the selection tray from explicit ids, or from a server-side filter. */
	initialSelectedIds?: string[];
	initialSelectedParams?: Record<string, string>;
	confirmLabel?: string;
	/** Receives the final selected ids on confirm. */
	onConfirm: (ids: string[]) => Promise<void> | void;
}

/**
 * Open the shared entity picker modal. Wraps the modal-store plumbing so a caller
 * only supplies the picker options.
 */
export function openEntityPicker(modalStore: ModalStore, options: EntityPickerOptions): void {
	const component: ModalComponent = {
		ref: EntityPickerModal,
		props: { ...options }
	};
	const modal: ModalSettings = {
		type: 'component',
		component,
		title: options.title
	};
	modalStore.trigger(modal);
}
