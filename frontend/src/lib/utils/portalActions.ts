import { m } from '$paraglide/messages';
import type { ModalStore } from '$lib/components/Modals/stores';

type Toast = { trigger: (s: { message: string; background: string }) => void };

// Confirm-then-submit the closest <form> of the clicked element (shared delete UX).
export const confirmDeleteForm = (modalStore: ModalStore, e: MouseEvent, name: string) => {
	const form = (e.currentTarget as HTMLElement).closest('form') as HTMLFormElement;
	modalStore.trigger({
		type: 'confirm',
		title: m.delete(),
		body: m.deleteModalMessage({ name }),
		buttonTextConfirm: m.delete(),
		response: (confirmed: boolean) => {
			if (confirmed) form.requestSubmit();
		}
	});
};
type EnhanceArgs = {
	result: { type: string };
	update: (opts?: { reset?: boolean }) => Promise<void>;
};

// Activate a tile on Enter/Space, for keyboard parity with onclick.
export const onActivateKey = (handler: () => void) => (e: KeyboardEvent) => {
	if (e.key === 'Enter' || e.key === ' ') {
		e.preventDefault();
		handler();
	}
};

export const savedToast = (toast: Toast) =>
	toast.trigger({ message: m.saved(), background: 'preset-filled-success-500' });

// use:enhance factory that fires a "saved" toast only when the action actually succeeds.
export const savedToastEnhance =
	(toast: Toast, opts?: { reset?: boolean }) =>
	() =>
	async ({ result, update }: EnhanceArgs) => {
		await update(opts);
		if (result.type === 'success') savedToast(toast);
	};
