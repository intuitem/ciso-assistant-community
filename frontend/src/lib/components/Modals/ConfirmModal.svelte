<script lang="ts">
	import type { urlModel } from '$lib/utils/types';

	// Props
	

	// Stores
	import type { ModalStore } from '@skeletonlabs/skeleton-svelte';

	import { m } from '$paraglide/messages';

	const modalStore: ModalStore = getModalStore();


	import { superForm } from 'sveltekit-superforms';

	import SuperForm from '$lib/components/Forms/Form.svelte';

	const { form } = superForm(_form, {
		dataType: 'json',
		id: `confirm-modal-form-${crypto.randomUUID()}`
	});

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container';

	import SuperDebug from 'sveltekit-superforms';
	import type { ComponentType } from 'svelte';
	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		_form?: any;
		URLModel?: urlModel | '';
		id?: string;
		formAction: string;
		bodyComponent: ComponentType | undefined;
		bodyProps?: Record<string, unknown>;
		debug?: boolean;
	}

	let {
		parent,
		_form = {},
		URLModel = '',
		id = '',
		formAction,
		bodyComponent,
		bodyProps = {},
		debug = false
	}: Props = $props();
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader}>{$modalStore[0].title ?? '(title missing)'}</header>
		<article>{$modalStore[0].body ?? '(body missing)'}</article>
		{#if bodyComponent}
			{@const SvelteComponent = bodyComponent}
			<div class="max-h-96 overflow-y-scroll scroll card">
				<SvelteComponent {...bodyProps} />
			</div>
		{/if}
		<!-- Enable for debugging: -->
		<SuperForm dataType="json" action={formAction} data={_form} class="modal-form {cForm}">
			<!-- prettier-ignore -->
			<footer class="modal-footer {parent.regionFooter}">
        <button type="button" class="btn {parent.buttonNeutral}" onclick={parent.onClose}>{m.cancel()}</button>
        <input type="hidden" name="urlmodel" value={URLModel} />
        <input type="hidden" name="id" value={id} />
        <button class="btn preset-filled-error-500" type="submit" onclick={parent.onConfirm}>{m.submit()}</button>
      </footer>
		</SuperForm>
		{#if debug === true}
			<SuperDebug data={$form} />
		{/if}
	</div>
{/if}
