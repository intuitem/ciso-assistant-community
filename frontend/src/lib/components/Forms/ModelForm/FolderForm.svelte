<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import FileInput from '../FileInput.svelte';
	import Checkbox from '../Checkbox.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';

	// Props unused but referenced to avoid browser warnings because they're needed for enterprise Folderform
	
	interface Props {
		form: SuperValidated<any>;
		importFolder?: boolean;
		// and there is only one ModelForm.
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		model: ModelInfo;
	}

	let {
		form,
		importFolder = false,
		cacheLocks = {},
		formDataCache = {},
		initialData = {},
		object = {},
		model
	}: Props = $props();
</script>

{#if importFolder}
	<FileInput
		{form}
		allowPaste={true}
		field="file"
		label={m.file()}
		allowedExtensions={['bak', 'zip']}
		helpText={m.importFolderHelpText()}
	/>
	<Checkbox
		{form}
		field="load_missing_libraries"
		label={m.loadMissingLibraries()}
		helpText={m.loadMissingLibrariesHelpText()}
	/>
{/if}
