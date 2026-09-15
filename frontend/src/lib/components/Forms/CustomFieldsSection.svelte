<script lang="ts">
	import TextField from './TextField.svelte';
	import NumberField from './NumberField.svelte';
	import Checkbox from './Checkbox.svelte';
	import Select from './Select.svelte';
	import AutocompleteSelect from './AutocompleteSelect.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import { fetchAllPages } from '$lib/utils/pagination';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { get } from 'svelte/store';
	import { type SuperForm } from 'sveltekit-superforms';

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

	/** Host form data; `custom_fields` is absent on create forms until a field mounts. */
	type HostFormData = Record<string, unknown> & { custom_fields?: Record<string, unknown> };

	/** The host form's superforms data store, read and pruned here. */
	const formData = (form as SuperForm<HostFormData>).form;

	/**
	 * Drop values whose definition no longer applies (e.g. after a domain change),
	 * otherwise they linger in the payload and the API rejects them as unknown keys.
	 * Payload-only: absent keys never touch values stored server-side.
	 */
	function pruneStaleValues(definitions: Definition[]) {
		const validKeys = new Set(definitions.map((definition) => definition.key));
		const current = get(formData)?.custom_fields;
		if (!current || !Object.keys(current).some((key) => !validKeys.has(key))) return;
		formData.update(
			(data) => {
				if (data.custom_fields) {
					for (const key of Object.keys(data.custom_fields)) {
						if (!validKeys.has(key)) delete data.custom_fields[key];
					}
				}
				return data;
			},
			{ taint: false }
		);
	}

	/**
	 * Mirrors the API's `_is_empty`. `false` counts as empty because the checkbox
	 * binding fabricates it on mount, so it never signals a value worth showing.
	 */
	const isEmptyValue = (v: unknown): boolean =>
		v == null ||
		v === false ||
		v === '' ||
		(Array.isArray(v) && v.length === 0) ||
		(typeof v === 'object' && Object.keys(v).length === 0);

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
			loaded = await fetchAllPages<Definition>(fetch, `/custom-fields/?${params.toString()}`);
		} catch (e) {
			console.error('Failed to load custom field definitions', e);
		}
		if (seq !== loadSeq) return;
		if (loaded === null) {
			// Render nothing rather than another folder's fields, but leave the
			// values alone: nothing says which keys are still valid.
			loadFailed = true;
			return;
		}
		definitions = loaded;
		pruneStaleValues(loaded);
		startOpen =
			loaded.some((d) => d.required) ||
			Object.values(get(formData)?.custom_fields ?? {}).some((v) => !isEmptyValue(v));
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
