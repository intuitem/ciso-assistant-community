<script lang="ts">
	import { getModalStore, type ModalStore } from './stores';
	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		url: string;
	}

	let { parent, url }: Props = $props();
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>
			<i class="fa-solid fa-circle-exclamation"></i>
			{m.externalLinkWarning()}
		</header>
		<article class="space-y-3">
			<p>{m.externalLinkConfirmMessage()}</p>
			<div class="code-block bg-surface-100 p-3 rounded-lg text-sm break-all">
				{url}
			</div>
			<p class="text-sm text-surface-600">
				{m.externalLinkVerifyMessage()}
			</p>
		</article>
		<footer class="modal-footer {parent.regionFooter} flex justify-end space-x-2">
			<button type="button" class="btn variant-ghost" onclick={parent.onClose}>
				{m.cancel()}
			</button>
			<button class="btn variant-filled-primary" type="button" onclick={parent.onConfirm}>
				{m.continue()}
			</button>
		</footer>
	</div>
{/if}
