<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Checkbox from '../Checkbox.svelte';
	import NumberField from '../NumberField.svelte';
	import TextArea from '../TextArea.svelte';
	import TextField from '../TextField.svelte';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {}
	}: {
		form: SuperValidated<Record<string, unknown>>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, unknown>;
		initialData?: Record<string, unknown>;
	} = $props();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="quick-forms"
	field="quick_form"
	cacheLock={cacheLocks['quick_form']}
	bind:cachedValue={formDataCache['quick_form']}
	label={m.quickForm()}
	hidden={initialData.quick_form}
/>
<TextField
	{form}
	field="name"
	label={m.name()}
	cacheLock={cacheLocks['name']}
	bind:cachedValue={formDataCache['name']}
	data-focusindex="0"
/>
<TextArea
	{form}
	field="description"
	label={m.description()}
	cacheLock={cacheLocks['description']}
	bind:cachedValue={formDataCache['description']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="submission_folder"
	cacheLock={cacheLocks['submission_folder']}
	bind:cachedValue={formDataCache['submission_folder']}
	label={m.submissionFolder()}
	helpText={m.quickFormSubmissionFolderHelpText()}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="user-groups"
	field="audience_groups"
	cacheLock={cacheLocks['audience_groups']}
	bind:cachedValue={formDataCache['audience_groups']}
	label={m.audienceGroups()}
	helpText={m.quickFormAudienceHelpText()}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="actors?is_third_party=false"
	field="default_reviewers"
	cacheLock={cacheLocks['default_reviewers']}
	bind:cachedValue={formDataCache['default_reviewers']}
	label={m.defaultReviewers()}
/>
<TextField
	{form}
	field="icon"
	label={m.icon()}
	cacheLock={cacheLocks['icon']}
	bind:cachedValue={formDataCache['icon']}
	helpText="fa-unlock-keyhole"
/>
<NumberField
	{form}
	field="order"
	label={m.order()}
	cacheLock={cacheLocks['order']}
	bind:cachedValue={formDataCache['order']}
/>
<Checkbox {form} field="enabled" label={m.enabled()} />
<Checkbox
	{form}
	field="allow_multiple_drafts"
	label={m.allowMultipleDrafts()}
	helpText={m.quickFormAllowMultipleDraftsHelpText()}
/>
