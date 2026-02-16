<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { modelSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { superForm } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import type { AnyZodObject } from 'zod';
	import { getModalStore, type ModalStore } from './stores';
	import { page } from '$app/state';
	import { invalidateAll } from '$app/navigation';

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-50 p-4 w-modal shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold whitespace-pre-line';

	interface Props {
		parent: any;
		form: SuperValidated<AnyZodObject>;
		urlModel: string;
		field: string;
		optionsEndpoint?: string;
		label?: string;
		optionsInfoFields?: {
			fields: { field: string; translate?: boolean }[];
			classes?: string;
		};
	}

	let {
		parent,
		form: formData,
		urlModel,
		field: fieldName,
		optionsEndpoint = '',
		label,
		optionsInfoFields = {
			fields: [],
			classes: 'text-surface-500'
		}
	}: Props = $props();

	const schema = modelSchema(urlModel);

	// Extract initial field value from SuperValidated data before creating superForm,
	// because formFieldProxy may not resolve it synchronously in Svelte 5 modal context.
	const initialFieldValue = formData.data?.[fieldName];

	const _form = superForm(formData, {
		dataType: 'json',
		taintedMessage: false,
		validators: zod(schema)
	});

	// Ensure the form store has the field value (workaround for formFieldProxy timing)
	if (initialFieldValue !== undefined) {
		_form.form.update((current: Record<string, any>) => ({
			...current,
			[fieldName]: initialFieldValue
		}));
	}

	let isSubmitting = $state(false);

	async function handleSubmit() {
		isSubmitting = true;
		try {
			// Read current field value from the form store
			let fieldValue: any;
			_form.form.subscribe((data: Record<string, any>) => {
				fieldValue = data[fieldName];
			})();

			// PATCH only the specific M2M field
			const objectId = page.params.id;
			const res = await fetch(`/${urlModel}/${objectId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ [fieldName]: fieldValue })
			});

			if (res.ok) {
				await invalidateAll();
				if (parent && typeof parent.onConfirm === 'function') {
					parent.onConfirm();
				}
			} else {
				const error = await res.json();
				console.error('Failed to update:', error);
			}
		} finally {
			isSubmitting = false;
		}
	}
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
		<div class="flex flex-col space-y-3">
			<AutocompleteSelect
				form={_form}
				multiple
				{optionsEndpoint}
				optionsExtraFields={[['folder', 'str']]}
				{optionsInfoFields}
				field={fieldName}
				label={safeTranslate(label ?? fieldName)}
			/>
			<div class="flex justify-end gap-2">
				<button type="button" class="btn preset-tonal" onclick={parent.onClose}>
					{m.cancel()}
				</button>
				<button
					type="button"
					class="btn preset-filled-primary-500"
					disabled={isSubmitting}
					onclick={handleSubmit}
				>
					{m.save()}
				</button>
			</div>
		</div>
	</div>
{/if}
