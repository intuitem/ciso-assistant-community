<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import { superForm } from 'sveltekit-superforms/client';
	import SuperDebug from 'sveltekit-superforms/client/SuperDebug.svelte';
	import type { AnyZodObject } from 'zod';

	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	const modalStore: ModalStore = getModalStore();

	export let data: SuperValidated<AnyZodObject>;
	export let dataType: 'form' | 'json';
	export let invalidateAll = true; // set to false to keep form data using muliple forms on a page
	export let validators: AnyZodObject;
	export let applyAction = true;
	export let resetForm = false;

	export let debug = false; // set to true to enable SuperDebug component

	function handleFormUpdated({
		form,
		closeModal
	}: {
		form: any;
		closeModal: boolean;
	}) {
		if (closeModal && form.valid) {
			$modalStore[0] ? modalStore.close() : null;
		}
	}

	export const _form = superForm(data, {
		dataType: dataType,
		invalidateAll: invalidateAll,
		applyAction: applyAction,
		resetForm: resetForm,
		validators: validators,
		onUpdated: ({ form }) => handleFormUpdated({ form, closeModal: true })
		
	});

	const { form, message /*, tainted*/, delayed, errors, allErrors, enhance } = _form;
</script>

{#if debug}
	<SuperDebug data={$form} />
	<SuperDebug data={$errors} />
{/if}

<form method="POST" use:enhance {...$$restProps}>
	{#if $errors._errors}
		{#each $errors._errors as error}
			<p class="text-error-500 text-sm font-medium">{error}</p>
		{/each}
	{/if}
	{#if $errors.non_field_errors}
		<p class="text-error-500 text-sm font-medium">{$errors.non_field_errors}</p>
	{/if}
	<slot
		form={_form}
		initialData={data.data}
		data={$form}
		message={$message}
		errors={$errors}
		allErrors={$allErrors}
		delayed={$delayed}
	/>
</form>
