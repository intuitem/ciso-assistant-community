<script lang="ts">
	import { superForm, type SuperValidated } from 'sveltekit-superforms';
	import { getModalStore, type ModalStore } from './stores';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import AutocompleteSelect from '../Forms/AutocompleteSelect.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import { z, type AnyZodObject } from 'zod';
	import * as m from '$paraglide/messages';
	import HiddenInput from '../Forms/HiddenInput.svelte';

	const modalStore: ModalStore = getModalStore();

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		parent: any;
		form: SuperValidated<AnyZodObject>;
		optionsEndpoint: string;
		field: string;
		fieldName: string;
	}

	let { parent, form, field, fieldName, optionsEndpoint }: Props = $props();

	const schema = z.object({
		urlModel: z.string(),
		[field]: z.string().uuid().array().optional()
	});

	const _form = superForm(form, {
		dataType: 'json',
		enctype: 'application/x-www-form-urlencoded',
		invalidateAll: true,
		validators: zod(schema),
		onUpdated: parent.onClose
	});
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<div class="flex items-center justify-between">
			<header class={cHeader} data-testid="modal-title">
				{$modalStore[0].title ?? '(title missing)'}
			</header>
			<div
				role="button"
				tabindex="0"
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
				onkeydown={parent.onClose}
			>
				<i class="fa-solid fa-xmark"></i>
			</div>
		</div>

		<SuperForm
			class="flex flex-col space-y-3"
			dataType="json"
			enctype="application/x-www-form-urlencoded"
			data={form}
			{_form}
			validators={zod(schema)}
			action="?/select"
		>
			<HiddenInput form={_form} field="urlModel" />
			<AutocompleteSelect
				form={_form}
				multiple
				{optionsEndpoint}
				optionsExtraFields={[['folder', 'str']]}
				{field}
				label={fieldName}
			/>
			<button class="btn preset-filled-primary-500 font-semibold w-full" type="submit"
				>{m.save()}</button
			>
		</SuperForm>
	</div>
{/if}
