<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		shape?: any;
		context?: string;
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

{#if shape.user_groups}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="user-groups"
		field="user_groups"
		pathField="path"
		cacheLock={cacheLocks['user_groups']}
		bind:cachedValue={formDataCache['user_groups']}
		label={m.userGroups()}
	/>
{/if}
