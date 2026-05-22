<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	type ActionType = 'approve' | 'reject' | 'revoke' | 'drop' | 'request_changes' | 'resubmit';

	interface Props {
		parent: any;
		action: ActionType;
		onConfirm: (notes: string) => Promise<void>;
		onSuccess: () => void;
	}

	let { parent, action, onConfirm, onSuccess }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	let notes = $state('');
	let isSubmitting = $state(false);
	let errorMessage = $state('');

	const actionTitles: Record<ActionType, string> = {
		approve: m.approve(),
		reject: m.reject(),
		revoke: m.revoke(),
		drop: m.drop(),
		request_changes: m.requestChanges(),
		resubmit: m.resubmit()
	};

	const actionIcons: Record<ActionType, string> = {
		approve: 'fa-check',
		reject: 'fa-times',
		revoke: 'fa-ban',
		drop: 'fa-trash',
		request_changes: 'fa-pencil',
		resubmit: 'fa-paper-plane'
	};

	const actionColors: Record<ActionType, string> = {
		approve: 'preset-filled-success-500',
		reject: 'preset-filled-error-500',
		revoke: 'preset-filled-warning-500',
		drop: 'preset-filled-surface-500',
		request_changes: 'preset-filled-warning-500',
		resubmit: 'preset-filled-primary-500'
	};

	async function handleConfirm() {
		if (isSubmitting) return;
		isSubmitting = true;
		errorMessage = '';
		try {
			await onConfirm(notes);
			parent.onClose();
			onSuccess();
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : String(e);
		} finally {
			isSubmitting = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div class="card bg-surface-50 p-6 w-full max-w-3xl shadow-xl space-y-5">
		<header class="flex justify-between items-center">
			<h2 class="text-xl font-bold capitalize">{actionTitles[action]}</h2>
			<button
				type="button"
				class="text-surface-500 hover:text-surface-700"
				onclick={() => {
					if (!isSubmitting) {
						parent.onClose();
					}
				}}
				disabled={isSubmitting}
				aria-label={m.close()}
			>
				<i class="fa-solid fa-times text-xl"></i>
			</button>
		</header>

		<div class="space-y-4">
			<div>
				<label for="validation-notes" class="block text-sm font-medium mb-2">
					{m.notes()}
				</label>
				<textarea
					id="validation-notes"
					bind:value={notes}
					class="textarea w-full"
					rows={4}
					placeholder={m.enterYourObservation()}
				></textarea>
			</div>

			{#if errorMessage}
				<div
					class="alert preset-filled-error-500 text-sm p-3 rounded"
					role="alert"
					aria-live="assertive"
				>
					{errorMessage}
				</div>
			{/if}
		</div>

		<footer class="flex justify-end space-x-2">
			<button
				type="button"
				class="btn preset-tonal-surface border border-surface-500"
				onclick={parent.onClose}
				disabled={isSubmitting}
			>
				{m.cancel()}
			</button>
			<button
				type="button"
				class="btn {actionColors[action]}"
				onclick={handleConfirm}
				disabled={isSubmitting}
			>
				{#if isSubmitting}
					<i class="fa-solid fa-spinner fa-spin mr-2"></i>
				{:else}
					<i class="fa-solid {actionIcons[action]} mr-2"></i>
				{/if}
				{m.confirm()}
			</button>
		</footer>
	</div>
{/if}
