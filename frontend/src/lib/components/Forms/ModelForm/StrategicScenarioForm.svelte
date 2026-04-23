<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import TextField from '$lib/components/Forms/TextField.svelte';

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

	function toSingleId(value: unknown): string | null {
		if (Array.isArray(value)) {
			return value.length > 0 && value[0] ? String(value[0]) : null;
		}

		if (value && typeof value === 'object' && 'id' in value && value.id) {
			return String(value.id);
		}

		return value ? String(value) : null;
	}

	const selectedRoToCoupleId = $derived(
		toSingleId(formDataCache['ro_to_couple']) ?? toSingleId(initialData.ro_to_couple)
	);
</script>

<p class="text-sm text-gray-500">{m.strategicScenarioHelpText()}</p>

<AutocompleteSelect
	{form}
	optionsEndpoint="ro-to?is_selected=true"
	optionsDetailedUrlParameters={[['ebios_rm_study', initialData.ebios_rm_study]]}
	optionsLabelField="str"
	field="ro_to_couple"
	cacheLock={cacheLocks['ro_to_couple']}
	bind:cachedValue={formDataCache['ro_to_couple']}
	label={m.roToCouple()}
/>
{#key selectedRoToCoupleId}
	<AutocompleteSelect
		{form}
		optionsEndpoint="feared-events"
		optionsDetailedUrlParameters={[
			['ebios_rm_study', initialData.ebios_rm_study],
			...(selectedRoToCoupleId ? [['ro_to_couples', selectedRoToCoupleId]] : [])
		]}
		optionsLabelField="auto"
		field="focused_feared_event"
		cacheLock={cacheLocks['focused_feared_event']}
		bind:cachedValue={formDataCache['focused_feared_event']}
		label={m.focusedFearedEvent()}
		nullable
	/>
{/key}
<FolderTreeSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.folder()}
	hidden
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
