<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		data?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		data = {}
	}: Props = $props();
</script>

<TextField
	{form}
	field="email"
	label={m.email()}
	cacheLock={cacheLocks['email']}
	bind:cachedValue={formDataCache['email']}
	data-focusindex="2"
/>
{#if !data.user}
	<Checkbox {form} field="create_user" label={m.createUser()} helpText={m.createUserHelpText()} />
{/if}
<AutocompleteSelect
	{form}
	optionsEndpoint="entities"
	field="entity"
	cacheLock={cacheLocks['entity']}
	bind:cachedValue={formDataCache['entity']}
	label={m.entity()}
/>
<TextField
	{form}
	field="first_name"
	label={m.firstName()}
	cacheLock={cacheLocks['first_name']}
	bind:cachedValue={formDataCache['first_name']}
/>
<TextField
	{form}
	field="last_name"
	label={m.lastName()}
	cacheLock={cacheLocks['last_name']}
	bind:cachedValue={formDataCache['last_name']}
/>
<TextField
	{form}
	field="phone"
	label={m.phone()}
	cacheLock={cacheLocks['phone']}
	bind:cachedValue={formDataCache['phone']}
/>
<TextField
	{form}
	field="role"
	label={m.role()}
	cacheLock={cacheLocks['role']}
	bind:cachedValue={formDataCache['role']}
/>
