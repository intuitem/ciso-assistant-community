<script lang="ts">
	import type { urlModel } from '$lib/utils/types';

	// Props
	/** Exposes parent props to this component. */
	export let parent: any;

	// Stores
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { ModalStore } from '@skeletonlabs/skeleton';

	import * as m from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	export let _form;
	export let URLModel: urlModel;
	export let formAction: string = '?/delete'
	export let invalidateAll = true; // set to false to keep form data using muliple forms on a page
	export let id: string;
	import { superForm } from 'sveltekit-superforms';

	const { form /*, message*/, enhance } = superForm(_form, {invalidateAll});

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	import SuperDebug from 'sveltekit-superforms';
	export let debug = false;
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>
		<!-- Enable for debugging: -->
		<form method="POST" action={formAction} class="modal-form {cForm}">
			<!-- prettier-ignore -->
			<footer class="modal-footer {parent.regionFooter}">
        <button type="button" class="btn {parent.buttonNeutral}" data-testid="delete-cancel-button" on:click={parent.onClose}>{m.cancel()}</button>
        <input type="hidden" name="delete" />
        <input type="hidden" name="urlmodel" value={URLModel} />
        <input type="hidden" name="id" value={id} />
        <button class="btn variant-filled-error" data-testid="delete-confirm-button" type="submit" on:click={parent.onClose}>{m.submit()}</button>
    </footer>
		</form>
		{#if debug === true}
			<SuperDebug data={$form} />
		{/if}
	</div>
{/if}
