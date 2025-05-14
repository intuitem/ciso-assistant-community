<script lang="ts">
	import type { urlModel } from '$lib/utils/types';

	// Props
	

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton-svelte';

	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();

	import { superForm } from 'sveltekit-superforms';

	const { form /*, message*/, enhance } = superForm(_form, { invalidateAll });

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container';

	import SuperDebug from 'sveltekit-superforms';
	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		_form: any;
		URLModel: urlModel;
		formAction?: string;
		invalidateAll?: boolean; // set to false to keep form data using muliple forms on a page
		id: string;
		debug?: boolean;
	}

	let {
		parent,
		_form,
		URLModel,
		formAction = '?/delete',
		invalidateAll = true,
		id,
		debug = false
	}: Props = $props();
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>
		<!-- Enable for debugging: -->
		<form method="POST" action={formAction} use:enhance class="modal-form {cForm}">
			<!-- prettier-ignore -->
			<footer class="modal-footer {parent.regionFooter}">
        <button type="button" class="btn {parent.buttonNeutral}" data-testid="delete-cancel-button" onclick={parent.onClose}>{m.cancel()}</button>
        <input type="hidden" name="urlmodel" value={URLModel} />
        <input type="hidden" name="id" value={id} />
        <button class="btn preset-filled-error-500" data-testid="delete-confirm-button" type="submit" onclick={parent.onClose}>{m.submit()}</button>
    </footer>
		</form>
		{#if debug === true}
			<SuperDebug data={$form} />
		{/if}
	</div>
{/if}
