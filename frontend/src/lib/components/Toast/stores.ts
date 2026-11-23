import { getContext, setContext } from 'svelte';
import { toast } from 'svelte-sonner';
import ToastCard, { type ToastTone } from './ToastCard.svelte';

export interface ToastSettings {
	/** Provide the toast message. Supports HTML. */
	message: string;
	/** Provide CSS classes to set the background color. */
	background?: string;
	/** Semantic color preset. Ignored when `background` is set. */
	preset?: 'error' | 'success' | 'warning';
	/** Enables auto-hide after the timeout duration. */
	autohide?: boolean;
	/** Set the auto-hide timeout duration. */
	timeout?: number;
	/** Generate a custom action button UI. */
	action?: {
		/** The button label. Supports HTML. */
		label: string;
		/** The function triggered when the button is pressed. */
		response: () => void;
	};
	/** Hide dismiss button */
	hideDismiss?: boolean;
	/** Remain visible on Hover */
	hoverable?: boolean;
	/** Provide arbitrary CSS classes to style the toast. */
	classes?: string;
	/** Callback function that fires on trigger and close. */
	callback?: (response: { id: string; status: 'queued' | 'closed' }) => void;
}

const toastDefaults: ToastSettings = {
	message: 'Missing Toast Message',
	autohide: true,
	timeout: 5000
};

const TOAST_STORE_KEY = 'toastStore';

/**
 * Retrieves the `toastStore`.
 *
 * This can *ONLY* be called from the **top level** of components!
 *
 * @example
 * ```svelte
 * <script>
 * 	import { getToastStore } from "#lib/components/Toast/stores.js";
 *
 * 	const toastStore = getToastStore();
 *
 * 	toastStore.open({ message: "Welcome!" });
 * </script>
 * ```
 */
export function getToastStore(): ToastStore {
	const toastStore = getContext<ToastStore | undefined>(TOAST_STORE_KEY);

	if (!toastStore)
		throw new Error(
			'toastStore is not initialized. Please ensure that `initializeStores()` is invoked in the root layout file of this app!'
		);

	return toastStore;
}

/**
 * Initializes the `toastStore`.
 */
export function initializeToastStore(): ToastStore {
	const toastStore = toastService();

	return setContext(TOAST_STORE_KEY, toastStore);
}

// Older callers pass a Skeleton background class instead of a preset.
function toneOf(t: ToastSettings): ToastTone {
	const hint = t.preset ?? t.background ?? '';
	if (hint.includes('error')) return 'error';
	if (hint.includes('success')) return 'success';
	if (hint.includes('warning')) return 'warning';
	return 'info';
}

export type ToastStore = ReturnType<typeof toastService>;
function toastService() {
	return {
		/** Show a toast; returns its id. */
		trigger: (settings: ToastSettings) => {
			const t = { ...toastDefaults, ...settings };
			// Same message, same id: a page with many tables can fail N times at once; show it once.
			const id = `toast:${t.message}`;
			const closed = () => t.callback?.({ id, status: 'closed' });
			toast.custom(ToastCard, {
				id,
				// hideDismiss always auto-hides, otherwise the toast could never go away.
				duration: t.autohide || t.hideDismiss ? t.timeout : Number.POSITIVE_INFINITY,
				dismissible: !t.hideDismiss,
				onDismiss: closed,
				onAutoClose: closed,
				componentProps: {
					message: t.message,
					tone: toneOf(t),
					action: t.action,
					hideDismiss: t.hideDismiss,
					classes: t.classes
				}
			});
			t.callback?.({ id, status: 'queued' });
			return id;
		},
		/** Remove a toast by id. */
		close: (id: string) => toast.dismiss(id),
		/** Remove all toasts. */
		clear: () => toast.dismiss()
	};
}
