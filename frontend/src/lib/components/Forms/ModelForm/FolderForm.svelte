<script lang="ts">
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import FileInput from '../FileInput.svelte';
	import Checkbox from '../Checkbox.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';

	export let form: SuperValidated<any>;
	export let importFolder: boolean = false;
	// Props unused but referenced to avoid browser warnings because they're needed for enterprise Folderform
	// and there is only one ModelForm.
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: any = {};
	export let model: ModelInfo;
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
