<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import * as m from '$paraglide/messages.js';
	import { getOptions } from '$lib/utils/crud';
	import TextArea from '../TextArea.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let context: string;
</script>

{#if context !== 'ebiosRmStudy'}
	<TextField
		{form}
		field="version"
		label={m.version()}
		cacheLock={cacheLocks['version']}
		bind:cachedValue={formDataCache['version']}
	/>
	<TextField
		{form}
		field="ref_id"
		label={m.refId()}
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
	/>
	<AutocompleteSelect
		{form}
		options={getOptions({ objects: model.foreignKeys['folder'] })}
		field="folder"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.domain()}
		hidden={initialData.folder}
	/>
	<AutocompleteSelect
		{form}
		options={getOptions({ objects: model.foreignKeys['risk_matrix'] })}
		field="risk_matrix"
		cacheLock={cacheLocks['risk_matrix']}
		bind:cachedValue={formDataCache['risk_matrix']}
		label={m.riskMatrix()}
		helpText={m.ebiosRmMatrixHelpText()}
	/>
{:else if context === 'ebiosRmStudy'}
	<div class="relative p-2 space-y-2 border rounded-md">
		<p class="absolute -top-3 bg-white font-bold">{m.activityOne()}</p>
		<TextField
			{form}
			field="version"
			label={m.version()}
			cacheLock={cacheLocks['version']}
			bind:cachedValue={formDataCache['version']}
		/>
		<TextField
			{form}
			field="ref_id"
			label={m.refId()}
			cacheLock={cacheLocks['ref_id']}
			bind:cachedValue={formDataCache['ref_id']}
		/>
		<TextArea
			{form}
			field="observation"
			label={m.observation()}
			cacheLock={cacheLocks['observation']}
			bind:cachedValue={formDataCache['observation']}
		/>
		<AutocompleteSelect
			multiple
			{form}
			options={getOptions({ objects: model.foreignKeys['authors'], label: 'email' })}
			field="authors"
			cacheLock={cacheLocks['authors']}
			bind:cachedValue={formDataCache['authors']}
			label={m.authors()}
		/>
		<AutocompleteSelect
			multiple
			{form}
			options={getOptions({ objects: model.foreignKeys['reviewers'], label: 'email' })}
			field="reviewers"
			cacheLock={cacheLocks['reviewers']}
			bind:cachedValue={formDataCache['reviewers']}
			label={m.reviewers()}
		/>
	</div>
	<div class="relative p-2 space-y-2 border rounded-md">
		<p class="absolute -top-3 bg-white font-bold">{m.activityTwo()}</p>
		<AutocompleteSelect
			multiple
			{form}
			options={getOptions({
				objects: model.foreignKeys['assets'],
				extra_fields: [['folder', 'str']],
				label: 'auto'
			})}
			field="assets"
			label={m.assets()}
		/>
	</div>
{/if}
