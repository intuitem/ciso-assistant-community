<script lang="ts">
	// Props
	

	// Stores
	import type { ModelInfo } from '$lib/utils/types';
	import type { ModalStore } from '@skeletonlabs/skeleton-svelte';
	const modalStore: ModalStore = getModalStore();

	let closeModal = true;

	// Base Classes
	const cBase = 'card p-4 w-fit max-w-4xl shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	interface Props {
		/** Exposes parent props to this component. */
		parent: any;
		form: SuperValidated<AnyZodObject>;
		customNameDescription?: boolean;
		importFolder?: boolean;
		model: ModelInfo;
		duplicate?: boolean;
		invalidateAll?: boolean; // set to false to keep form data using muliple forms on a page
		formAction?: string;
		context?: string;
		additionalInitialData?: any;
		suggestions?: { [key: string]: any };
		taintedMessage?: string | boolean;
		debug?: boolean;
		[key: string]: any
	}

	let {
		parent,
		form,
		customNameDescription = false,
		importFolder = false,
		model,
		duplicate = false,
		invalidateAll = true,
		formAction = '?/create',
		context = 'create',
		additionalInitialData = {},
		suggestions = {},
		taintedMessage = false,
		debug = false,
		...rest
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
			{form}
			{customNameDescription}
			{importFolder}
			{additionalInitialData}
			{suggestions}
			{parent}
			{invalidateAll}
			{model}
			{closeModal}
			{context}
			{duplicate}
			{taintedMessage}
			caching={true}
			action={formAction}
			{debug}
			{...rest}
		/>
	</div>
{/if}
