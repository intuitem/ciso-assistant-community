<script lang="ts">
	import FileInput from '../FileInput.svelte';
    import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: any = {};
    export let importFolder: boolean = false;
</script>

{#if importFolder}
    <TextField
        {form}
        field="name"
        label={m.name()}
        cacheLock={cacheLocks['name']}
        bind:cachedValue={formDataCache['name']}
        data-focusindex="0"
    />
    <FileInput
        {form}
        allowPaste={true}
        field="dump"
        label={m.attachment()}
        allowedExtensions={'*'}
    />
{/if}