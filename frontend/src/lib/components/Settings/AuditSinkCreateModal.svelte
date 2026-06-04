<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Form from '$lib/components/Forms/Form.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import RadioGroup from '$lib/components/Forms/RadioGroup.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { auditSinkSchema } from '$lib/utils/schemas';
	import { m } from '$paraglide/messages';
	import { onMount, tick } from 'svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { superForm } from 'sveltekit-superforms/client';

	const cBase = 'card bg-surface-50 p-4 shadow-xl space-y-4';
	const cHeader = 'text-2xl font-bold';

	interface Props {
		parent: any;
		form: SuperForm<any>;
		formAction?: string;
		[key: string]: any;
	}

	const modalStore: ModalStore = getModalStore();

	let { parent, form, formAction = '?/createAuditSink' }: Props = $props();

	onMount(async () => {
		await tick();
		const firstField = document.querySelector('input[data-focusindex="0"]');
		if (firstField instanceof HTMLElement) {
			firstField.focus();
		}
	});

	const _form = superForm(form, {
		dataType: 'json',
		validators: zod(auditSinkSchema),
		validationMethod: 'onsubmit',
		onUpdated: async ({ form }) => {
			if (form.valid && parent && typeof parent.onConfirm === 'function') {
				parent.onConfirm();
			}
		}
	});
</script>

{#if $modalStore[0]}
	<div class="w-2xl {cBase}">
		<div class="flex items-center justify-between">
			<header class={cHeader} data-testid="modal-title">
				{$modalStore[0].title ?? '(title missing)'}
			</header>
			<div
				role="button"
				tabindex="0"
				class="flex items-center hover:text-primary-500 cursor-pointer"
				onclick={parent.onClose}
				onkeydown={(e) => {
					if (e.key === 'Enter' || e.key === ' ') {
						e.preventDefault();
						parent.onClose(e);
					}
				}}
			>
				<i class="fa-solid fa-xmark"></i>
			</div>
		</div>
		<Form
			class="flex flex-col space-y-3"
			{_form}
			data={form}
			dataType="json"
			validators={zod(auditSinkSchema)}
			action={formAction}
		>
			{#snippet children({ form })}
				<Checkbox {form} field="is_active" label={m.isActive()} checked />
				<TextField {form} field="name" label={m.name()} data-focusindex="0" />
				<MarkdownField {form} field="description" label={m.description()} />
				<TextField {form} field="url" label={m.url()} autocomplete="off" />
				<RadioGroup
					{form}
					field="body_format"
					label={m.bodyFormat()}
					possibleOptions={[
						{ label: 'OCSF', value: 'ocsf' },
						{ label: m.raw(), value: 'raw' }
					]}
					labelKey="label"
					valueKey="value"
					helpText={m.bodyFormatHelpText()}
				/>
				<TextField
					{form}
					field="headers"
					label={m.httpHeaders()}
					autocomplete="off"
					helpText={m.httpHeadersHelpText()}
				/>
				<AutocompleteSelect
					{form}
					field="target_folders"
					label={m.targetDomains()}
					helpText={m.auditSinkTargetDomainsHelpText()}
					optionsEndpoint="folders?content_type=DO&content_type=GL"
					multiple
				/>
				<div class="flex flex-row justify-between space-x-4">
					<button
						class="btn bg-gray-400 text-white font-semibold w-full"
						data-testid="cancel-button"
						type="button"
						onclick={(event) => {
							parent.onClose(event);
						}}>{m.cancel()}</button
					>
					<button class="btn preset-filled-primary-500 font-semibold w-full" type="submit"
						>{m.save()}</button
					>
				</div>
			{/snippet}
		</Form>
	</div>
{/if}
