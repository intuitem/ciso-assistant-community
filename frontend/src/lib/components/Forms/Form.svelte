<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import { superForm } from 'sveltekit-superforms';
	import SuperDebug from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	// import type { ModalStore } from '@skeletonlabs/skeleton-svelte';
	// const modalStore: ModalStore = getModalStore();

	import { m } from '$paraglide/messages';

	function handleFormUpdated({ form, closeModal }: { form: any; closeModal: boolean }) {
		if (form.valid) {
			onUpdated(form);
			// if (closeModal) $modalStore[0] ? modalStore.close() : null;
		}
	}

	interface Props {
		data?: SuperValidated<AnyZodObject>;
		dataType?: 'form' | 'json';
		invalidateAll?: boolean; // set to false to keep form data using muliple forms on a page
		validators?: AnyZodObject | undefined;
		applyAction?: boolean;
		resetForm?: boolean;
		onSubmit?: any;
		taintedMessage?: string | null;
		onUpdated?: any;
		validationMethod?: 'auto' | 'oninput' | 'onblur' | 'onsubmit' | 'submit-only';
		useFocusTrap?: boolean;
		debug?: boolean; // set to true to enable SuperDebug component
		_form?: any;
		children?: import('svelte').Snippet<[any]>;
		[key: string]: any;
	}

	let {
		data = {},
		dataType = 'form',
		invalidateAll = true,
		validators = undefined,
		applyAction = true,
		resetForm = false,
		onSubmit = (submit_data: any) => {},
		taintedMessage = m.taintedFormMessage(),
		onUpdated = (_: any) => {},
		validationMethod = 'auto',
		useFocusTrap = true,
		debug = false,
		_form = superForm(data, {
			dataType: dataType,
			invalidateAll: invalidateAll,
			applyAction: applyAction,
			resetForm: resetForm,
			validators: validators,
			onUpdated: ({ form }) => handleFormUpdated({ form, closeModal: true }),
			onSubmit: onSubmit,
			taintedMessage: taintedMessage,
			validationMethod
		}),
		children,
		...rest
	}: Props = $props();

	const { form, message, tainted, delayed, errors, allErrors, enhance } = _form;
</script>

{#if debug}
	<SuperDebug data={$form} />
	<SuperDebug data={$tainted} />
	<SuperDebug data={$errors} />
{/if}

<form method="POST" use:enhance {...rest}>
	{#if $errors._errors}
		{#each $errors._errors as error}
			<p class="text-error-500 text-sm font-medium">{error}</p>
		{/each}
	{/if}
	{#if $errors.non_field_errors}
		<p class="text-error-500 text-sm font-medium">{$errors.non_field_errors}</p>
	{/if}
	{@render children?.({
		form: _form,
		initialData: data?.data,
		data: $form,
		formData: $form,
		message: $message,
		errors: $errors,
		allErrors: $allErrors,
		delayed: $delayed,
		tainted: $tainted
	})}
</form>
