<script lang="ts">
	import { getModalStore, type ModalStore } from './stores';
	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	// Base Classes
	const cBase = 'card bg-surface-100-900 border border-surface-500 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		missing: { id: string; label: string }[];
	}

	let { parent, missing }: Props = $props();
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{m.submitForReview()}</header>
		<article class="space-y-3">
			{#if missing.length}
				<p class="font-medium">
					<i class="fa-solid fa-paperclip mr-2 text-warning-600-400"
					></i>{m.missingEvidenceBeforeSubmission()}
				</p>
				<ul
					class="max-h-64 overflow-y-auto list-disc list-inside text-sm text-surface-700-300 border border-surface-300-700 rounded-md px-4 py-3 space-y-1"
					data-testid="submit-missing-evidence-list"
				>
					{#each missing as item (item.id)}
						<li>{item.label}</li>
					{/each}
				</ul>
			{:else}
				<p>{m.submitForReviewConfirm()}</p>
			{/if}
		</article>
		<footer class="modal-footer {parent.regionFooter} flex justify-end space-x-2">
			<button type="button" class="btn preset-outlined" onclick={parent.onClose}>
				{m.cancel()}
			</button>
			<button
				class="btn preset-filled-primary-500"
				type="button"
				disabled={missing.length > 0}
				onclick={parent.onConfirm}
				data-testid="submit-assignment-confirm"
			>
				{m.submitForReview()}
			</button>
		</footer>
	</div>
{/if}
