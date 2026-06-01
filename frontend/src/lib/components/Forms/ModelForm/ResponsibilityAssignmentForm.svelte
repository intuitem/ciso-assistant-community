<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
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

	const activityHidden = context === 'fromBaseModel';
</script>

{#if !activityHidden}
	<AutocompleteSelect
		{form}
		optionsEndpoint="pmbok/responsibility-matrix-activities"
		optionsLabelField="auto"
		field="activity"
		cacheLock={cacheLocks['activity']}
		bind:cachedValue={formDataCache['activity']}
		label={m.responsibilityActivity()}
		disabled={!!initialData.activity}
	/>
{/if}

<AutocompleteSelect
	{form}
	optionsEndpoint="actors"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="actor"
	cacheLock={cacheLocks['actor']}
	bind:cachedValue={formDataCache['actor']}
	label={m.actor()}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="pmbok/responsibility-roles?is_visible=true"
	optionsLabelField="auto"
	optionsExtraFields={[['code', 'str']]}
	field="role"
	cacheLock={cacheLocks['role']}
	bind:cachedValue={formDataCache['role']}
	label={m.role()}
/>
