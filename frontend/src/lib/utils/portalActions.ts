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
	result: { type: string; data?: { error?: unknown }; error?: { message?: string } };
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

// Actions fail with the backend's raw body: {"field": ["msg"]} or {"detail": "msg"}.
// Surface the first message in it rather than the JSON.
const firstMessage = (value: unknown): string | undefined => {
	if (typeof value === 'string') return value || undefined;
	if (value && typeof value === 'object') {
		for (const v of Object.values(value)) {
			const found = firstMessage(v);
			if (found) return found;
		}
	}
	return undefined;
};

const readableError = (raw: unknown): string => {
	if (typeof raw !== 'string') return firstMessage(raw) ?? m.error();
	try {
		return firstMessage(JSON.parse(raw)) ?? m.error();
	} catch {
		return raw || m.error();
	}
};

// Toast the reason a failed action gives. No-op on success/redirect.
export const failureToast = (toast: Toast, result: EnhanceArgs['result']) => {
	if (result.type !== 'failure' && result.type !== 'error') return;
	toast.trigger({
		message: readableError(result.type === 'failure' ? result.data?.error : result.error?.message),
		background: 'preset-filled-error-500'
	});
};

// use:enhance factory: a "saved" toast when the action succeeds, its reason when not.
export const savedToastEnhance =
	(toast: Toast, opts?: { reset?: boolean }) =>
	() =>
	async ({ result, update }: EnhanceArgs) => {
		await update(opts);
		if (result.type === 'success') savedToast(toast);
		else failureToast(toast, result);
	};
