<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import { superForm } from 'sveltekit-superforms';
	import SuperDebug from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import { focusTrap } from '@skeletonlabs/skeleton';

	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	const modalStore: ModalStore = getModalStore();

	import * as m from '$paraglide/messages';

	export let data: SuperValidated<AnyZodObject>;
	export let dataType: 'form' | 'json';
	export let invalidateAll = true; // set to false to keep form data using muliple forms on a page
	export let validators: AnyZodObject;
	export let applyAction = true;
	export let resetForm = false;
	export let onSubmit = (submit_data: any) => {};
	export let taintedMessage: string | null = m.taintedFormMessage();
	export let onUpdated = (_: any) => {};

	export let useFocusTrap = true;

	export let debug = false; // set to true to enable SuperDebug component

	function handleFormUpdated({ form, closeModal }: { form: any; closeModal: boolean }) {
		if (form.valid) {
			onUpdated(form);
			if (closeModal)
				$modalStore[0] ? modalStore.close() : null;
		}
	}

	export const _form = superForm(data, {
		dataType: dataType,
		invalidateAll: invalidateAll,
		applyAction: applyAction,
		resetForm: resetForm,
		validators: validators,
		onUpdated: ({ form }) => handleFormUpdated({ form, closeModal: true }),
		onSubmit: onSubmit,
		taintedMessage: taintedMessage
	});

	const { form, message, tainted, delayed, errors, allErrors, enhance } = _form;
</script>

{#if debug}
	<SuperDebug data={$form} />
	<SuperDebug data={$tainted} />
	<SuperDebug data={$errors} />
{/if}

<form method="POST" use:enhance use:focusTrap={useFocusTrap} {...$$restProps}>
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
		tainted={$tainted}
	/>
</form>
