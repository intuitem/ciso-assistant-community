<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import { getOptions } from '$lib/utils/crud';
	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let shape: any = {};
</script>

{#if model.urlModel === 'users'}
	<TextField
		{form}
		field="email"
		label={m.email()}
		cacheLock={cacheLocks['email']}
		bind:cachedValue={formDataCache['email']}
		data-focusindex="2"
	/>
	{#if shape.first_name && shape.last_name}
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
	{/if}
	{#if shape.user_groups}
		<AutocompleteSelect
			{form}
			multiple
			options={getOptions({ objects: model.foreignKeys['user_groups'] })}
			field="user_groups"
			cacheLock={cacheLocks['user_groups']}
			bind:cachedValue={formDataCache['user_groups']}
			label={m.userGroups()}
		/>
	{/if}
	{#if shape.is_active}
		<Checkbox {form} field="is_active" label={m.isActive()} helpText={m.isActiveHelpText()} />
	{/if}
{/if}
