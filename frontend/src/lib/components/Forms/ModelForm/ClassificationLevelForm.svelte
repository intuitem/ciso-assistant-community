<script lang="ts">
	import Checkbox from '../Checkbox.svelte';
	import TextField from '../TextField.svelte';
	import NumberField from '../NumberField.svelte';
	import MarkdownField from '../MarkdownField.svelte';
	import TranslationField from '../TranslationField.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
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
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	const { value: hexcolor } = formFieldProxy(form, 'hexcolor');
</script>

{#if !object.builtin}
	<AutocompleteSelect
		{form}
		field="object_classification"
		optionsEndpoint="object-classifications"
		label={m.objectClassification()}
		cacheLock={cacheLocks['object_classification']}
		bind:cachedValue={formDataCache['object_classification']}
		hidden={Boolean(initialData?.object_classification)}
	/>
	<TextField
		{form}
		field="abbreviation"
		label={m.abbreviation()}
		cacheLock={cacheLocks['abbreviation']}
		bind:cachedValue={formDataCache['abbreviation']}
		data-focusindex="0"
	/>
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
	/>
	<MarkdownField
		{form}
		field="description"
		label={m.description()}
		cacheLock={cacheLocks['description']}
		bind:cachedValue={formDataCache['description']}
	/>
	<NumberField
		{form}
		field="rank"
		label={m.rank()}
		cacheLock={cacheLocks['rank']}
		bind:cachedValue={formDataCache['rank']}
	/>
	<label class="label">
		<span class="text-sm font-semibold">{m.color()}</span>
		<div class="flex items-center gap-2">
			<input type="color" bind:value={$hexcolor} class="h-10 w-16 cursor-pointer rounded" />
			<input type="text" bind:value={$hexcolor} class="input w-28" placeholder="#RRGGBB" />
		</div>
	</label>
	<TranslationField
		{form}
		field="translations"
		cacheLock={cacheLocks['translations']}
		bind:cachedValue={formDataCache['translations']}
	/>
{/if}
<Checkbox {form} field="is_visible" label={m.isVisible()} helpText={m.isVisibleHelpText()} />
