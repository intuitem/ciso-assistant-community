<script lang="ts">
	import Checkbox from '../Checkbox.svelte';
	import Select from '../Select.svelte';
	import TextField from '../TextField.svelte';
	import NumberField from '../NumberField.svelte';
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
	import NestedTranslationField from '../NestedTranslationField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { formFieldProxy } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = 'default'
	}: Props = $props();

	const isEdit = $derived(Boolean(object?.id));

	const modelOptions = [
		{ label: m.project(), value: 'pmbok.project' },
		{ label: m.asset(), value: 'core.asset' },
		{ label: m.appliedControl(), value: 'core.appliedcontrol' }
	];

	const { value: fieldType } = formFieldProxy(form, 'field_type');
	const isChoice = $derived($fieldType === 'choice' || $fieldType === 'multi_choice');

	// Definition-level translations {locale: {label, help_text}}, synced for submission.
	const { value: translationsValue } = formFieldProxy(form, 'translations');
	let translations: Record<string, Record<string, string>> = $state(
		($translationsValue as any) || {}
	);
	$effect(() => {
		$translationsValue = $state.snapshot(translations);
	});

	const translationSubfields = [
		{ key: 'label', label: m.label() },
		{ key: 'help_text', label: m.helpText() }
	];

	// Inline choices editor, synced into form.data.choices for submission.
	const { value: choicesValue } = formFieldProxy(form, 'choices');
	type ChoiceRow = {
		value: string;
		label: string;
		order: number;
		translations: Record<string, Record<string, string>>;
	};
	let choices: ChoiceRow[] = $state(
		Array.isArray($choicesValue) ? $choicesValue.map((c: any) => ({ translations: {}, ...c })) : []
	);
	$effect(() => {
		$choicesValue = $state.snapshot(choices);
	});

	function addChoice() {
		choices = [...choices, { value: '', label: '', order: choices.length, translations: {} }];
	}
	function removeChoice(i: number) {
		choices = choices.filter((_, idx) => idx !== i).map((c, idx) => ({ ...c, order: idx }));
	}
</script>

{#if !isEdit}
	<Select
		{form}
		options={modelOptions}
		field="model"
		label={m.model ? m.model() : 'Model'}
		cacheLock={cacheLocks['model']}
		bind:cachedValue={formDataCache['model']}
	/>
{/if}

<FolderTreeSelect
	{form}
	field="folder"
	label={m.domain()}
	helpText={m.customFieldFolderHelpText()}
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
/>

<TextField
	{form}
	field="key"
	label={m.key()}
	helpText={m.customFieldKeyHelpText()}
	disabled={isEdit}
	cacheLock={cacheLocks['key']}
	bind:cachedValue={formDataCache['key']}
/>

<TextField
	{form}
	field="label"
	label={m.label()}
	cacheLock={cacheLocks['label']}
	bind:cachedValue={formDataCache['label']}
/>

<TextField
	{form}
	field="help_text"
	label={m.helpText()}
	cacheLock={cacheLocks['help_text']}
	bind:cachedValue={formDataCache['help_text']}
/>

<NestedTranslationField bind:value={translations} subfields={translationSubfields} />

<Select
	{form}
	options={model.selectOptions['field_type'] ?? []}
	field="field_type"
	label={m.fieldType()}
	disabled={isEdit}
	cacheLock={cacheLocks['field_type']}
	bind:cachedValue={formDataCache['field_type']}
/>

{#if isChoice}
	<div class="border rounded-container-token p-3 space-y-2 bg-surface-50">
		<div class="flex items-center justify-between">
			<span class="text-sm font-semibold">{m.choices()}</span>
			<button type="button" class="btn btn-sm variant-soft-primary" onclick={addChoice}>
				<i class="fa-solid fa-plus mr-1"></i>{m.addChoice()}
			</button>
		</div>
		{#if choices.length === 0}
			<p class="text-sm text-surface-500 italic">{m.noChoiceAdded()}</p>
		{/if}
		{#each choices as choice, i (i)}
			<div class="border rounded-container-token p-2 bg-surface-100-800-token space-y-2">
				<div class="flex gap-2 items-end">
					<label class="flex-1 text-xs">
						{m.value()}
						<input type="text" class="input" bind:value={choice.value} placeholder="gold" />
					</label>
					<label class="flex-1 text-xs">
						{m.label()}
						<input type="text" class="input" bind:value={choice.label} placeholder="Gold" />
					</label>
					<button
						type="button"
						class="btn-icon variant-soft-error"
						onclick={() => removeChoice(i)}
						title={m.delete()}
					>
						<i class="fa-solid fa-trash"></i>
					</button>
				</div>
				<NestedTranslationField
					bind:value={choice.translations}
					subfields={[{ key: 'label', label: m.label() }]}
				/>
			</div>
		{/each}
	</div>
{/if}

<div class="flex flex-wrap gap-x-6 gap-y-2">
	<Checkbox {form} field="required" label={m.required()} />
	<Checkbox {form} field="visible" label={m.visible()} />
	<Checkbox
		{form}
		field="searchable"
		label={m.searchable()}
		helpText={m.customFieldSearchableHelpText()}
	/>
	<Checkbox {form} field="filterable" label={m.filterable()} />
</div>

<NumberField
	{form}
	field="order"
	label={m.order()}
	cacheLock={cacheLocks['order']}
	bind:cachedValue={formDataCache['order']}
/>
