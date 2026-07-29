import EntityPickerModal from '$lib/components/Modals/EntityPickerModal.svelte';
import type { ModalComponent, ModalSettings, ModalStore } from '$lib/components/Modals/stores';

export interface EntityPickerOptions {
	/** API resource whose `/{endpoint}/autocomplete` action backs the picker. */
	endpoint: string;
	title?: string;
	subtitle?: string;
	/** Object field or dot-path used as the primary row label (default 'str'). */
	labelField?: string;
	/** Optional secondary text shown after the label (e.g. 'email', 'folder.str'). */
	secondaryField?: string;
	/** Fixed query params applied to every request (e.g. scoping filters). */
	scopeFilters?: Record<string, string>;
	/** Boolean field driving an active/inactive badge + an "include inactive" toggle. */
	activeField?: string;
	confirmLabel?: string;
	/**
	 * Receives the selected ids on confirm. Selection is scoped to the visible
	 * page; on success the picker stays open and reloads, so larger scopes are
	 * composed page by page, confirm by confirm (add-only scope filters drop
	 * confirmed items from subsequent pages). Throw to keep the selection and
	 * surface the failure.
	 */
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
