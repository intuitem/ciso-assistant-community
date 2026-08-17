<script lang="ts">
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

<TextField
	{form}
	field="name"
	label={m.name()}
	cacheLock={cacheLocks['name']}
	bind:cachedValue={formDataCache['name']}
/>
<TextField
	{form}
	disabled={context === 'edit'}
	field="provider_id"
	label={m.providerId()}
	helpText={m.providerIdHelpText()}
	cacheLock={cacheLocks['provider_id']}
	bind:cachedValue={formDataCache['provider_id']}
/>
<TextField
	{form}
	field="client_id"
	label={m.clientId()}
	helpText={m.clientIDHelpText()}
	cacheLock={cacheLocks['client_id']}
	bind:cachedValue={formDataCache['client_id']}
/>
<TextField
	{form}
	field="server_url"
	label={m.serverUrl()}
	helpText={m.serverUrlHelpText()}
	cacheLock={cacheLocks['server_url']}
	bind:cachedValue={formDataCache['server_url']}
/>
