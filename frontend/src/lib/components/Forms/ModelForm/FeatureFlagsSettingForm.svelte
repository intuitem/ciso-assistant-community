<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	import { ffNav } from '$lib/components/SideBar/ffNav';
	export let data: any = {};
</script>

<AutocompleteSelect
	{form}
	field="feature_flags"
	cacheLock={cacheLocks['feature_flags']}
	bind:cachedValue={formDataCache['feature_flags']}
	options={model.selectOptions['feature_flags']}
	label={m.featuredFlags()}
/>
