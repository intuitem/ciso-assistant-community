<script lang="ts">
	export type ToastTone = 'success' | 'error' | 'warning' | 'info';

	interface Props {
		message: string;
		tone: ToastTone;
		action?: { label: string; response: () => void };
		hideDismiss?: boolean;
		classes?: string;
		closeToast?: () => void;
	}

	let { message, tone, action, hideDismiss = false, classes = '', closeToast }: Props = $props();

	const toneStyle: Record<ToastTone, { icon: string; color: string }> = {
		success: { icon: 'fa-circle-check', color: 'text-success-600-400' },
		error: { icon: 'fa-circle-exclamation', color: 'text-error-600-400' },
		warning: { icon: 'fa-triangle-exclamation', color: 'text-warning-600-400' },
		info: { icon: 'fa-circle-info', color: 'text-primary-600-400' }
	};
	const style = $derived(toneStyle[tone]);
</script>

<div
	class="flex w-[min(100vw-2rem,26rem)] items-start gap-3 rounded-xl border border-surface-200-800 bg-surface-50-950 py-3 pl-3.5 pr-2 text-surface-950-50 shadow-[0_8px_24px_-8px_rgb(15_23_42/0.25)] {classes}"
	role={tone === 'error' ? 'alert' : 'status'}
	data-testid="toast"
	data-tone={tone}
>
	<i class="fa-solid {style.icon} {style.color} mt-0.5 text-base" aria-hidden="true"></i>
	<p class="min-w-0 flex-1 text-sm leading-5 break-words">{message}</p>
	{#if action}
		<button
			type="button"
			class="shrink-0 rounded-md px-2 py-1 text-sm font-medium text-primary-700-300 hover:bg-surface-100-900"
			onclick={() => {
				action.response();
				closeToast?.();
			}}>{action.label}</button
		>
	{/if}
	{#if !hideDismiss}
		<button
			type="button"
			class="shrink-0 size-7 -my-0.5 rounded-md text-surface-500 hover:bg-surface-100-900 hover:text-surface-900-100"
			aria-label="Dismiss toast"
			onclick={() => closeToast?.()}><i class="fa-solid fa-xmark" aria-hidden="true"></i></button
		>
	{/if}
</div>
