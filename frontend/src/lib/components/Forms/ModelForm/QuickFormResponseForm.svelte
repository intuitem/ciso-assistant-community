<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '../Checkbox.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		context: string;
	}

	let {
		form,
		model = $bindable(),
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="quick-forms"
	optionsLabelField="name"
	field="quick_form"
	cacheLock={cacheLocks['quick_form']}
	bind:cachedValue={formDataCache['quick_form']}
	label={m.quickForm()}
	hidden={initialData.quick_form}
	disabled={context === 'edit'}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors?is_third_party=false"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		classes: 'text-blue-500'
	}}
	field="respondents"
	cacheLock={cacheLocks['respondents']}
	bind:cachedValue={formDataCache['respondents']}
	label={m.respondents()}
	helpText={m.quickFormRespondentsHelpText()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors?is_third_party=false"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		classes: 'text-blue-500'
	}}
	field="reviewers"
	cacheLock={cacheLocks['reviewers']}
	bind:cachedValue={formDataCache['reviewers']}
	label={m.reviewers()}
	helpText={m.quickFormReviewersHelpText()}
/>
<TextField
	type="date"
	{form}
	field="due_date"
	label={m.dueDate()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
{#if context === 'create'}
	<Checkbox
		{form}
		field="start_now"
		label={m.startNow()}
		helpText={m.startNowHelpText()}
		cacheLock={cacheLocks['start_now']}
		bind:cachedValue={formDataCache['start_now']}
	/>
{/if}
