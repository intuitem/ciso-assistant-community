<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { m } from '$paraglide/messages';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import { page } from '$app/state';

	interface Props {
		form: SuperValidated<any>;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
	}

	let { form, cacheLocks = {}, formDataCache = $bindable({}) }: Props = $props();
</script>

<TextField
	{form}
	field="version"
	label={m.version()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>
