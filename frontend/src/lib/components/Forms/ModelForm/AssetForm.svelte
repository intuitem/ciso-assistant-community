<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import Score from '../Score.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: any = {};
	export let data: any = {};
</script>

<TextArea
	{form}
	field="business_value"
	label={m.businessValue()}
	cacheLock={cacheLocks['business_value']}
	bind:cachedValue={formDataCache['business_value']}
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
<Select
	{form}
	options={model.selectOptions['type']}
	field="type"
	label="Type"
	cacheLock={cacheLocks['type']}
	bind:cachedValue={formDataCache['type']}
/>
<AutocompleteSelect
	disabled={data.type === 'PR'}
	multiple
	{form}
	options={getOptions({ objects: model.foreignKeys['parent_assets'], self: object })}
	field="parent_assets"
	cacheLock={cacheLocks['parent_assets']}
	bind:cachedValue={formDataCache['parent_assets']}
	label={m.parentAssets()}
/>
<Score {form} label={m.confidentiality()} field="confidentiality" always_enabled={true} inversedColors fullDonut max_score={3} />
<Score {form} label={m.integrity()} field="integrity" always_enabled={true} inversedColors fullDonut max_score={3} />
<Score {form} label={m.availability()} field="availability" always_enabled={true} inversedColors fullDonut max_score={3} />
<Score {form} label={m.proof()} field="proof" always_enabled={true} inversedColors fullDonut max_score={3} />
<Score {form} label={m.authenticity()} field="authenticity" always_enabled={true} inversedColors fullDonut max_score={3} />
<Score {form} label={m.privacy()} field="privacy" always_enabled={true} inversedColors fullDonut max_score={3} />
<Score {form} label={m.safety()} field="safety" always_enabled={true} inversedColors fullDonut max_score={3} />
<NumberField
	{form}
	field="rto"
	label={m.rto()}
	positiveOnly
	helpText={m.rtoHelpText()}
	cacheLock={cacheLocks['rto']}
	bind:cachedValue={formDataCache['rto']}
/>
<NumberField
	{form}
	field="rpo"
	label={m.rpo()}
	positiveOnly
	helpText={m.rpoHelpText()}
	cacheLock={cacheLocks['rpo']}
	bind:cachedValue={formDataCache['rpo']}
/>
<NumberField
	{form}
	field="mtd"
	label={m.mtd()}
	positiveOnly
	helpText={m.mtdHelpText()}
	cacheLock={cacheLocks['mtd']}
	bind:cachedValue={formDataCache['mtd']}
/>
