<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		onConfirm: (gracePeriodMinutes: number) => void;
	}

	let { parent, onConfirm }: Props = $props();

	const MAX_GRACE_PERIOD_MINUTES = 31 * 24 * 60;
	const UNIT_MINUTES: Record<string, number> = {
		MINUTES: 1,
		HOURS: 60,
		DAYS: 24 * 60,
		WEEKS: 7 * 24 * 60
	};

	let hasGracePeriod = $state(false);
	let interval = $state(1);
	let unit = $state('HOURS');

	let gracePeriodMinutes = $derived(
		hasGracePeriod ? Math.max(0, Math.round(interval)) * UNIT_MINUTES[unit] : 0
	);
	let tooLong = $derived(gracePeriodMinutes > MAX_GRACE_PERIOD_MINUTES);

	function confirm() {
		if (tooLong) return;
		modalStore.close();
		onConfirm(gracePeriodMinutes);
	}

	function cancel() {
		if (parent && typeof parent.onClose === 'function') {
			parent.onClose();
		} else {
			modalStore.close();
		}
	}

	// Base Classes
	const cBase = 'card bg-surface-50-950 p-4 w-modal shadow-xl space-y-4';
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
					<span class="font-semibold text-sm text-surface-950-50">{m.each()}</span>
					<input
						type="number"
						min="1"
						class="input w-24"
						bind:value={interval}
						data-testid="grace-period-interval"
					/>
					<select class="select" bind:value={unit} data-testid="grace-period-unit-select">
						<option value="MINUTES">{m.minutes()}</option>
						<option value="HOURS">{m.hours()}</option>
						<option value="DAYS">{m.days()}</option>
						<option value="WEEKS">{m.weeks()}</option>
					</select>
				</div>
				{#if tooLong}
					<p class="text-sm text-error-500">{m.gracePeriodTooLong()}</p>
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
				disabled={tooLong}
				onclick={confirm}
				data-testid="confirm-rotate-secret-button">{m.submit()}</button
			>
		</footer>
	</div>
{/if}
