<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		onConfirm: (gracePeriodDays: number) => void;
	}

	let { parent, onConfirm }: Props = $props();

	const MAX_GRACE_PERIOD_DAYS = 30;

	let hasGracePeriod = $state(false);
	let days: number = $state(1);

	let invalid = $derived(
		hasGracePeriod && (!Number.isInteger(days) || days < 1 || days > MAX_GRACE_PERIOD_DAYS)
	);
	let gracePeriodDays = $derived(hasGracePeriod ? days : 0);

	function confirm() {
		if (invalid) return;
		modalStore.close();
		onConfirm(gracePeriodDays);
	}

	function cancel() {
		if (parent && typeof parent.onClose === 'function') {
			parent.onClose();
		} else {
			modalStore.close();
		}
	}

	// Base Classes
	const cBase = 'card bg-surface-100-900 border border-surface-500 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{m.rotateSecret()}</header>
		<article>{m.rotateSecretConfirm()}</article>
		<div class="space-y-2">
			<label class="flex items-center gap-2 font-semibold">
				<input type="checkbox" class="checkbox" bind:checked={hasGracePeriod} />
				{m.gracePeriod()}
			</label>
			{#if hasGracePeriod}
				<div class="flex w-full items-center space-x-3">
					<input
						type="number"
						min="1"
						max={MAX_GRACE_PERIOD_DAYS}
						class="input w-24"
						bind:value={days}
						data-testid="grace-period-days"
					/>
					<span class="font-semibold text-sm text-surface-950-50">{m.days()}</span>
				</div>
				{#if invalid}
					<p class="text-sm text-error-500">{m.gracePeriodInvalid()}</p>
				{/if}
			{/if}
			<p class="text-sm opacity-75">{m.gracePeriodHelpText()}</p>
		</div>
		<footer class="modal-footer {parent?.regionFooter ?? ''}">
			<button type="button" class="btn {parent?.buttonNeutral ?? ''}" onclick={cancel}
				>{m.cancel()}</button
			>
			<button
				class="btn preset-filled-error-500"
				type="button"
				disabled={invalid}
				onclick={confirm}
				data-testid="confirm-rotate-secret-button">{m.submit()}</button
			>
		</footer>
	</div>
{/if}
