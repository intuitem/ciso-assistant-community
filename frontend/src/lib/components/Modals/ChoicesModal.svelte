<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { getModalStore, type ModalStore } from './stores';
	import { superForm } from 'sveltekit-superforms';
	import SuperForm from '$lib/components/Forms/Form.svelte';

	interface Choice {
		name: string;
		description: string;
		action: string;
	}

	interface Props {
		parent: any;
		_form?: any;
		formAction?: string;
		title?: string;
		message?: string;
		choices?: Choice[];
		schema?: any;
	}

	let {
		parent,
		_form = {},
		formAction = '',
		title = 'Choices required',
		message = '',
		choices = [],
		schema
	}: Props = $props();

	// Base Classes
	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';
	const cForm = 'p-4 space-y-4 rounded-container';

	const modalStore: ModalStore = getModalStore();

	const { form } = superForm(_form, {
		dataType: 'json',
		id: `choices-modal-form-${crypto.randomUUID()}`
	});
</script>

{#if $modalStore[0]}
	<div class="modal-example-form {cBase}">
		<header class={cHeader} data-testid="modal-title">
			{title}
		</header>
		<span>{safeTranslate(message)}</span>
		<SuperForm
			dataType="json"
			action={formAction}
			data={_form}
			class="modal-form {cForm}"
			validators={schema}
			onsubmit={(e) => {
				e.preventDefault();
			}}
		>
			{#if choices && choices.length > 0}
				<div class="grid grid-cols-3 gap-x-8 gap-y-4">
					{#each choices as choice}
						<button
							class="badge bg-primary-50"
							type="submit"
							onclick={(e) => {
								e.currentTarget.form.action += `&action=${choice.action}`;
								parent.onConfirm();
							}}>{choice.name}<i class="fa-solid fa-info-circle"></i></button
						>
					{/each}
				</div>
			{/if}
		</SuperForm>
	</div>
{/if}
