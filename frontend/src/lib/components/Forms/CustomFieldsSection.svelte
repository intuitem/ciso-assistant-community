<script lang="ts">
	import TextField from './TextField.svelte';
	import NumberField from './NumberField.svelte';
	import Checkbox from './Checkbox.svelte';
	import Select from './Select.svelte';
	import AutocompleteSelect from './AutocompleteSelect.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { get } from 'svelte/store';

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
	let loadFailed = $state(false);
	// Expanded by default only when there's something the user must see: a
	// required field, or values already set (edit mode). Computed once per
	// definitions load so a manual toggle isn't overridden by form edits.
	let startOpen = $state(false);

	const formData = form.form;

	// Drop values whose definition no longer applies (e.g. after a domain change),
	// otherwise they linger in the payload and the API rejects them as unknown
	// keys. Payload-only: absent keys never touch values stored server-side.
	function pruneStaleValues(validKeys: Set<string>) {
		const current = get(formData)?.custom_fields;
		if (!current || !Object.keys(current).some((key) => !validKeys.has(key))) return;
		formData.update(
			(data: any) => {
				if (data?.custom_fields) {
					for (const key of Object.keys(data.custom_fields)) {
						if (!validKeys.has(key)) delete data.custom_fields[key];
					}
				}
				return data;
			},
			{ taint: false }
		);
	}

	// `false` excluded: the checkbox binding fabricates it on mount.
	const hasValue = (v: unknown) =>
		v != null && v !== false && v !== '' && !(Array.isArray(v) && v.length === 0);

	let loadSeq = 0;

	async function load(folder: string | undefined) {
		const seq = ++loadSeq;
		// Hide the previous folder's fields while the new set loads, so nothing
		// out of scope can be edited in the in-flight window. Write-only: reading
		// `definitions` here would make it a dependency of the calling $effect
		// and the post-response write would loop it. Values are kept until the
		// response tells which keys are still valid (folders can share keys).
		definitions = [];
		loadFailed = false;
		// for_folder is always sent: empty means "no folder chosen yet" and the
		// API resolves it to the global definitions only.
		const params = new URLSearchParams({ model, visible: 'true', for_folder: folder ?? '' });
		let loaded: Definition[] | null = null;
		try {
			const res = await fetch(`/custom-fields/?${params.toString()}`);
			if (res.ok) {
				const data = await res.json();
				loaded = data.results ?? data;
			}
		} catch (e) {
			console.error('Failed to load custom field definitions', e);
		}
		if (seq !== loadSeq) return;
		// On failure render nothing rather than another folder's fields: the
		// payload must only ever carry keys of currently rendered definitions.
		definitions = loaded ?? [];
		loadFailed = loaded === null;
		pruneStaleValues(new Set(definitions.map((d) => d.key)));
		startOpen =
			definitions.some((d) => d.required) ||
			Object.values(get(formData)?.custom_fields ?? {}).some(hasValue);
	}

	$effect(() => {
		if (enabled) load(folderId);
	});

	const choiceOptions = (def: Definition) =>
		def.choices.map((c) => ({ label: c.label_localized, value: c.value }));
</script>

{#if loadFailed}
	<p class="text-error-500 text-xs font-medium">{m.customFieldsLoadError()}</p>
{:else if definitions.length}
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
				{:else if def.field_type === 'url'}
					<TextField
						{form}
						type="url"
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
