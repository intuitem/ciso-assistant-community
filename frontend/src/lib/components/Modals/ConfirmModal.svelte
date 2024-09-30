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
	export let id: string;
	export let formAction: string;
	export let bodyComponent: ComponentType | undefined;
	export let bodyProps: Record<string, unknown> = {};

	import { superForm } from 'sveltekit-superforms';

	import SuperForm from '$lib/components/Forms/Form.svelte';

	const { form } = superForm(_form, {
		dataType: 'json',
		id: `confirm-modal-form-${crypto.randomUUID()}`
	});

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container-token';

	import SuperDebug from 'sveltekit-superforms';
	import type { ComponentType } from 'svelte';
	export let debug = false;
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>
		{#if bodyComponent}
			<div class="max-h-96 overflow-y-scroll scroll card">
				<svelte:component this={bodyComponent} {...bodyProps} />
			</div>
		{/if}
		<!-- Enable for debugging: -->
		<SuperForm dataType="json" action={formAction} data={_form} class="modal-form {cForm}">
			<!-- prettier-ignore -->
			<footer class="modal-footer {parent.regionFooter}">
        <button type="button" class="btn {parent.buttonNeutral}" on:click={parent.onClose}>{m.cancel()}</button>
        <input type="hidden" name="urlmodel" value={URLModel} />
        <input type="hidden" name="id" value={id} />
        <button class="btn variant-filled-error" type="submit" on:click={parent.onConfirm}>{m.submit()}</button>
      </footer>
		</SuperForm>
		{#if debug === true}
			<SuperDebug data={$form} />
		{/if}
	</div>
{/if}
