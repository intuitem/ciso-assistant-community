<script lang="ts">
	import Checkbox from '../Checkbox.svelte';
	import TextField from '../TextField.svelte';
	import MarkdownField from '../MarkdownField.svelte';
	import AssetClassTreeSelect from '../TreeSelect/AssetClassTreeSelect.svelte';
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
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	const { value: translationsValue } = formFieldProxy(form, 'translations');
	let translations: Record<string, Record<string, string>> = $state(
		($translationsValue as any) || {}
	);
	$effect(() => {
		$translationsValue = $state.snapshot(translations);
	});

	const translationSubfields = [
		{ key: 'name', label: m.name() },
		{ key: 'description', label: m.description() }
	];
</script>

{#if object.builtin}
	<aside class="alert preset-outlined-warning-500 text-sm">
		<i class="fa-solid fa-lock"></i>
		<span>{m.builtinAssetClassHelpText()}</span>
	</aside>
{:else}
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
		data-focusindex="0"
	/>
	<MarkdownField
		{form}
		field="description"
		label={m.description()}
		cacheLock={cacheLocks['description']}
		bind:cachedValue={formDataCache['description']}
	/>
	<AssetClassTreeSelect
		{form}
		field="parent"
		label={m.parentAssetClass()}
		cacheLock={cacheLocks['parent']}
		bind:cachedValue={formDataCache['parent']}
		excludeSubtreeOf={object.id ?? null}
		visibleOnly={false}
		hidden={Boolean(initialData?.parent)}
	/>
	<NestedTranslationField bind:value={translations} subfields={translationSubfields} />
{/if}
<Checkbox {form} field="is_visible" label={m.isVisible()} helpText={m.hiddenAssetClassHelpText()} />
