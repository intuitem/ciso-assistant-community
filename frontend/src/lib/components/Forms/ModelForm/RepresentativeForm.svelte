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
		object?: any;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		object = {},
		context = 'default'
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
{#if context === 'edit' && object.user}
	<div
		class="flex items-center gap-2 px-3 py-2.5 bg-secondary-50-950 rounded-md border-l-3 border-secondary-500"
	>
		<svg
			class="w-4 h-4 text-secondary-600-400 flex-shrink-0"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
			></path>
		</svg>
		<div class="text-sm text-secondary-900-100">
			{m.userLinkedToRepresentative()}
		</div>
	</div>
{:else}
	<Checkbox
		{form}
		field="create_user"
		label={m.createUser()}
		helpText={m.createUserHelpText()}
		bind:cachedValue={formDataCache['create_user']}
	/>
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
