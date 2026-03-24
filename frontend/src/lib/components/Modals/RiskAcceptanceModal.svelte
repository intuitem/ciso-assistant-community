<script lang="ts">
	import type { urlModel } from '$lib/utils/types';
	import SuperDebug from 'sveltekit-superforms';
	import type { ComponentType } from 'svelte';
	import { getModalStore, type ModalStore } from './stores';
	import { m } from '$paraglide/messages';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container';

	interface Props {
		parent: any;
		_form?: any;
		URLModel?: urlModel | '';
		id?: string;
		formAction: string;
		bodyComponent?: ComponentType | undefined;
		bodyProps?: Record<string, unknown>;
		debug?: boolean;
		schema?: any;
	}

	let {
		parent,
		_form = {},
		URLModel = '',
		id = '',
		formAction,
		bodyComponent = undefined,
		bodyProps = {},
		debug = false,
		schema
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

		<SuperForm
			data={_form}
			dataType="json"
			action={formAction}
			class="modal-form {cForm}"
			validators={schema}
		>
			{#snippet children({ form })}
				<TextArea
					{form}
					field="justification"
					label={m.riskAcceptanceJustificationLabel()}
					helpText={m.riskAcceptanceJusitficationHelpText()}
				/>

				<footer class="modal-footer {parent.regionFooter}">
					<button
						type="button"
						class="btn {parent.buttonNeutral}"
						onclick={parent.onClose}
					>
						{m.cancel()}
					</button>
					<input type="hidden" name="urlmodel" value={URLModel} />
					<input type="hidden" name="id" value={id} />
					<button
						class="btn preset-filled-error-500"
						type="submit"
						onclick={parent.onConfirm}
					>
						{m.submit()}
					</button>
				</footer>
			{/snippet}
		</SuperForm>

		{#if debug}
			<SuperDebug data={_form} />
		{/if}
	</div>
{/if}
