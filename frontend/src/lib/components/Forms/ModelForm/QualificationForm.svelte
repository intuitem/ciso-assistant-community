<script lang="ts">
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import type { CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';

	interface Props {
		form: SuperValidated<any>;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
	}

	let { form, cacheLocks = {}, formDataCache = $bindable({}) }: Props = $props();
</script>

<TextField
	{form}
	field="abbreviation"
	label={m.abbreviation()}
	cacheLock={cacheLocks['abbreviation']}
	bind:cachedValue={formDataCache['abbreviation']}
/>
<TextArea
	{form}
	field="annotation"
	label={m.annotation()}
	cacheLock={cacheLocks['annotation']}
	bind:cachedValue={formDataCache['annotation']}
/>
<NumberField
	{form}
	field="qualification_ordering"
	label={m.qualificationOrdering()}
	cacheLock={cacheLocks['qualification_ordering']}
	bind:cachedValue={formDataCache['qualification_ordering']}
/>
<NumberField
	{form}
	field="security_objective_ordering"
	label={m.securityObjectiveOrdering()}
	cacheLock={cacheLocks['security_objective_ordering']}
	bind:cachedValue={formDataCache['security_objective_ordering']}
/>
