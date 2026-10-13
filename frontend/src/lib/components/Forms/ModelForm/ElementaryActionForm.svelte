<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {}
	}: Props = $props();

	const formStore = (form as any).form;

	// A technique fills what the user hasn't written yet
	async function prefill(id: string | null) {
		if (!id) return;
		const res = await fetch(`/techniques/${id}`);
		if (!res.ok) return;
		const technique = await res.json();
		formStore.update((data: Record<string, any>) => ({
			...data,
			name: data.name || technique.name,
			description: data.description || technique.description || ''
		}));
	}
</script>

<AutocompleteSelect
	{form}
	nullable
	optionsEndpoint="techniques"
	field="technique"
	optionsLabelField="auto"
	cacheLock={cacheLocks['technique']}
	bind:cachedValue={formDataCache['technique']}
	label={m.technique()}
	helpText={m.elementaryActionTechniqueHelp()}
	onChange={prefill}
/>
<Select
	{form}
	options={model.selectOptions['attack_stage']}
	field="attack_stage"
	label={m.attackStage()}
	disableDoubleDash
	cacheLock={cacheLocks['attack_stage']}
	bind:cachedValue={formDataCache['attack_stage']}
/>
<AutocompleteSelect
	{form}
	nullable
	optionsEndpoint="threats"
	field="threat"
	optionsLabelField="auto"
	cacheLock={cacheLocks['threat']}
	bind:cachedValue={formDataCache['threat']}
	label={m.threat()}
/>
<Select
	{form}
	options={model.selectOptions['icon']}
	field="icon"
	label={m.icon()}
	cacheLock={cacheLocks['icon']}
	bind:cachedValue={formDataCache['icon']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="operating-modes"
	field="operating_modes"
	cacheLock={cacheLocks['operating_modes']}
	bind:cachedValue={formDataCache['operating_modes']}
	label={m.operatingModes()}
	hidden
/>
