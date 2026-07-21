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

	let gracePeriodMinutes = $state(0);

	function confirm() {
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
			<label class="label font-semibold" for="grace-period-select">{m.gracePeriod()}</label>
			<select
				id="grace-period-select"
				class="select"
				bind:value={gracePeriodMinutes}
				data-testid="grace-period-select"
			>
				<option value={0}>{m.gracePeriodImmediate()}</option>
				<option value={15}>{m.gracePeriodMinutesOption({ minutes: 15 })}</option>
				<option value={30}>{m.gracePeriodMinutesOption({ minutes: 30 })}</option>
				<option value={60}>{m.gracePeriodMinutesOption({ minutes: 60 })}</option>
			</select>
			<p class="text-sm opacity-75">{m.gracePeriodHelpText()}</p>
		</div>
		<footer class="modal-footer {parent?.regionFooter ?? ''}">
			<button type="button" class="btn {parent?.buttonNeutral ?? ''}" onclick={cancel}
				>{m.cancel()}</button
			>
			<button
				class="btn preset-filled-error-500"
				type="button"
				onclick={confirm}
				data-testid="confirm-rotate-secret-button">{m.submit()}</button
			>
		</footer>
	</div>
{/if}
