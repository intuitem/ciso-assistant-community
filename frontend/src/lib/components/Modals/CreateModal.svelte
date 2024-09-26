<script lang="ts">
	// Props
	/** Exposes parent props to this component. */
	export let parent: any;

	// Stores
	import type { ModelInfo } from '$lib/utils/types';
	import type { ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';

	const modalStore: ModalStore = getModalStore();

	export let form: SuperValidated<AnyZodObject>;
	export let model: ModelInfo;
	export let riskAssessmentDuplication = false;
	export let invalidateAll = true; // set to false to keep form data using muliple forms on a page
	export let formAction = '?/create';
	export let context = 'default';
	let closeModal = true;
	export let suggestions: { [key: string]: any } = {};

	// Base Classes
	const cBase = 'card p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	export let debug = false;

	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
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
				on:click={parent.onClose}
				on:keydown={parent.onClose}
			>
				<i class="fa-solid fa-xmark" />
			</div>
		</div>
		<ModelForm
			{form}
			{suggestions}
			{parent}
			{invalidateAll}
			{model}
			{closeModal}
			context="create"
			{riskAssessmentDuplication}
			caching={true}
			action={formAction}
			{debug}
		/>
	</div>
{/if}
