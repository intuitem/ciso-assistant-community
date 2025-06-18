// Modal Store Queue

import { writable } from 'svelte/store';
import { getContext, setContext } from 'svelte';

const MODAL_STORE_KEY = 'modalStore';

// Modal Types

export interface ModalComponent {
	/** Import and provide your component reference. */
	ref: any;
	/** Provide component props as key/value pairs. */
	props?: Record<string, unknown>;
	/** Provide an HTML template literal for the default slot. */
	slot?: string;
}

export interface ModalSettings {
	/** Designate what type of component will display. */
	type: 'alert' | 'confirm' | 'prompt' | 'component';
	/** Set the modal position within the backdrop container. */
	position?: string;
	/** Provide the modal header content. Accepts HTML. */
	title?: string;
	/** Provide the modal body content. Accepts HTML. */
	body?: string;
	/** Provide a URL to display an image within the modal. */
	image?: string;
	/** By default, used to provide a prompt value. */
	value?: any;
	/** Provide input attributes as key/value pairs. */
	valueAttr?: object;
	/** Provide your component reference key or object. */
	component?: ModalComponent | string;
	/** Provide a function. Returns the response value. */
	response?: (r: any) => void;
	/** Provide arbitrary classes to the backdrop. */
	backdropClasses?: string;
	/** Provide arbitrary classes to the modal window. */
	modalClasses?: string;
	/** Override the Cancel button label. */
	buttonTextCancel?: string;
	/** Override the Confirm button label. */
	buttonTextConfirm?: string;
	/** Override the Submit button label. */
	buttonTextSubmit?: string;
	/** Pass arbitrary data per modal instance. */
	meta?: any;
}

/**
 * Retrieves the `modalStore`.
 *
 * This can *ONLY* be called from the **top level** of components!
 *
 * @example
 * ```svelte
 * <script>
 * 	import { getModalStore } from "@skeletonlabs/skeleton";
 *
 * 	const modalStore = getModalStore();
 *
 * 	modalStore.trigger({ type: "alert", title: "Welcome!" });
 * </script>
 * ```
 */
export function getModalStore(): ModalStore {
	const modalStore = getContext<ModalStore | undefined>(MODAL_STORE_KEY);

	if (!modalStore)
		throw new Error(
			'modalStore is not initialized. Please ensure that `initializeStores()` is invoked in the root layout file of this app!'
		);

	return modalStore;
}

/**
 * Initializes the `modalStore`.
 */
export function initializeModalStore(): ModalStore {
	const modalStore = modalService();

	return setContext(MODAL_STORE_KEY, modalStore);
}

export type ModalStore = ReturnType<typeof modalService>;
function modalService() {
	const { subscribe, set, update } = writable<ModalSettings[]>([]);
	return {
		subscribe,
		set,
		update,
		/** Append to end of queue. */
		trigger: (modal: ModalSettings) =>
			update((mStore) => {
				mStore.push(modal);
				return mStore;
			}),
		/**  Remove first item in queue. */
		close: () =>
			update((mStore) => {
				if (mStore.length > 0) mStore.shift();
				return mStore;
			}),
		/** Remove all items from queue. */
		clear: () => set([])
	};
}
