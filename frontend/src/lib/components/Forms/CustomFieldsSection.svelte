<script lang="ts">
	import TextField from './TextField.svelte';
	import NumberField from './NumberField.svelte';
	import Checkbox from './Checkbox.svelte';
	import Select from './Select.svelte';
	import AutocompleteSelect from './AutocompleteSelect.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';

	interface Choice {
		value: string;
		label_localized: string;
	}
	interface Definition {
		id: string;
		key: string;
		label_localized: string;
		help_text_localized?: string;
		field_type: string;
		required: boolean;
		choices: Choice[];
	}

	interface Props {
		form: any;
		/** app_label.model of the host */
		model: string;
		/** folder id used to resolve which definitions apply (global + ancestors) */
		folderId?: string;
	}

	let { form, model, folderId = undefined }: Props = $props();

	const enabled = $derived(page.data?.featureflags?.custom_fields === true);

	let definitions: Definition[] = $state([]);

	// Ensure the nested container exists before any field proxy writes into it.
	if (form.data && !form.data.custom_fields) form.data.custom_fields = {};

	async function load(folder: string | undefined) {
		const params = new URLSearchParams({ model, visible: 'true' });
		if (folder) params.set('for_folder', folder);
		try {
			const res = await fetch(`/custom-fields/?${params.toString()}`);
			if (!res.ok) return;
			const data = await res.json();
			definitions = data.results ?? data;
		} catch (e) {
			console.error('Failed to load custom field definitions', e);
		}
	}

	$effect(() => {
		if (enabled) load(folderId);
	});

	const choiceOptions = (def: Definition) =>
		def.choices.map((c) => ({ label: c.label_localized, value: c.value }));

	// Expanded by default only when there's something the user must see:
	// a required field, or values already set (edit mode). Otherwise collapsed.
	const startOpen = $derived(
		definitions.some((d) => d.required) ||
			Object.keys(form?.data?.custom_fields ?? {}).length > 0
	);
</script>

{#if definitions.length}
	<Dropdown open={startOpen} icon="fa-solid fa-sliders" header={m.customFields()} style="">
		<div class="space-y-3 pt-2">
			{#each definitions as def (def.id)}
			{@const path = `custom_fields.${def.key}`}
			{#if def.field_type === 'text'}
				<TextField
					{form}
					field={path}
					label={def.label_localized}
					helpText={def.help_text_localized}
					required={def.required}
				/>
			{:else if def.field_type === 'number'}
				<NumberField
					{form}
					field={path}
					label={def.label_localized}
					helpText={def.help_text_localized}
					required={def.required}
				/>
			{:else if def.field_type === 'date'}
				<TextField
					{form}
					type="date"
					field={path}
					label={def.label_localized}
					helpText={def.help_text_localized}
					required={def.required}
				/>
			{:else if def.field_type === 'boolean'}
				<Checkbox
					{form}
					field={path}
					label={def.label_localized}
					helpText={def.help_text_localized}
				/>
			{:else if def.field_type === 'choice'}
				<Select
					{form}
					field={path}
					options={choiceOptions(def)}
					label={def.label_localized}
					helpText={def.help_text_localized}
				/>
			{:else if def.field_type === 'multi_choice'}
				<AutocompleteSelect
					{form}
					multiple
					field={path}
					options={choiceOptions(def)}
					label={def.label_localized}
					helpText={def.help_text_localized}
				/>
			{/if}
			{/each}
		</div>
	</Dropdown>
{/if}
