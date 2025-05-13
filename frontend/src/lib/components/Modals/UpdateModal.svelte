<script lang="ts">
	// Props
	

	// Stores
	import type { ModelInfo } from '$lib/utils/types';
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	const modalStore: ModalStore = getModalStore();

	let closeModal = true;

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		form: SuperValidated<AnyZodObject>;
		model: ModelInfo;
		invalidateAll?: boolean; // set to false to keep form data using muliple forms on a page
		formAction?: string;
		context?: string;
		object?: Record<string, any>;
		suggestions?: { [key: string]: any };
		selectOptions?: Record<string, any>;
		debug?: boolean;
	}

	let {
		parent,
		form,
		model,
		invalidateAll = true,
		formAction = '?/update',
		context = 'default',
		object = {},
		suggestions = {},
		selectOptions = {},
		debug = false
	}: Props = $props();
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
		<ModelForm
			customNameDescription
			{form}
			{object}
			{suggestions}
			{parent}
			action={formAction}
			{invalidateAll}
			{model}
			{closeModal}
			{context}
			caching={true}
			{selectOptions}
			{debug}
		/>
	</div>
{/if}
