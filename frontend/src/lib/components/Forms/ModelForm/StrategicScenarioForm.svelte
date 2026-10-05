<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context
	}: Props = $props();
</script>

<p class="text-sm text-surface-600-400">{m.strategicScenarioHelpText()}</p>

<AutocompleteSelect
	{form}
	optionsEndpoint="ro-to?is_selected=true"
	optionsDetailedUrlParameters={[['ebios_rm_study', initialData.ebios_rm_study]]}
	optionsLabelField="str"
	field="ro_to_couple"
	cacheLock={cacheLocks['ro_to_couple']}
	bind:cachedValue={formDataCache['ro_to_couple']}
	label={m.roToCouple()}
	helpText={m.strategicScenarioRoToHelpText()}
/>
{#key formDataCache['ro_to_couple'] || initialData.ro_to_couple}
	<AutocompleteSelect
		{form}
		optionsEndpoint="feared-events"
		optionsDetailedUrlParameters={[
			['ebios_rm_study', initialData.ebios_rm_study],
			['ro_to_couples', formDataCache['ro_to_couple'] || initialData.ro_to_couple]
		]}
		optionsLabelField="auto"
		field="focused_feared_event"
		cacheLock={cacheLocks['focused_feared_event']}
		bind:cachedValue={formDataCache['focused_feared_event']}
		label={m.focusedFearedEvent()}
		helpText={m.strategicScenarioFocusedFearedEventHelpText()}
		nullable
	/>
{/key}
<Select
	{form}
	options={(model.selectOptions?.['gravity'] ?? []).filter((o) => o.value !== -1)}
	field="gravity_forced"
	label={m.forcedGravity()}
	helpText={m.forcedGravityHelpText()}
	cacheLock={cacheLocks['gravity_forced']}
	bind:cachedValue={formDataCache['gravity_forced']}
/>
