<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		shape?: any;
		context: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		shape = {},
		context
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>
<TextField
	{form}
	field="team_email"
	label={m.teamEmail()}
	cacheLock={cacheLocks['team_email']}
	bind:cachedValue={formDataCache['team_email']}
	data-focusindex="2"
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="leader"
	cacheLock={cacheLocks['leader']}
	bind:cachedValue={formDataCache['leader']}
	label={m.leader()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="deputies"
	cacheLock={cacheLocks['deputies']}
	bind:cachedValue={formDataCache['deputies']}
	label={m.deputies()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="members"
	cacheLock={cacheLocks['members']}
	bind:cachedValue={formDataCache['members']}
	label={m.members()}
/>
