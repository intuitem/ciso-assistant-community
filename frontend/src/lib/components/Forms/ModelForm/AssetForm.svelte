<script lang="ts">
	import { page } from '$app/stores';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { SECURITY_OBJECTIVE_SCALE_MAP } from '$lib/utils/constants';
	import { getOptions } from '$lib/utils/crud';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import type { SuperValidated } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import RadioGroupInput from '../RadioGroupInput.svelte';
	import Select from '../Select.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: any = {};
	export let data: any = {};

	type SecurityObjectiveScale = '0-3' | '1-4' | 'FIPS-199';
	const scale: SecurityObjectiveScale = $page.data.settings.security_objective_scale;
	const securityObjectiveScaleMap: string[] = SECURITY_OBJECTIVE_SCALE_MAP[scale];

	interface Option {
		label: string;
		value: number;
		suggested?: boolean;
	}

	const createOption = (label: string, value: number): Option => ({
		label,
		value
	});

	// Helper function to filter duplicate consecutive labels
	const filterDuplicateLabels = (options: Option[]): Option[] =>
		options.map((option, index, arr) => ({
			...option,
			label: index > 0 && option.label === arr[index - 1].label ? '' : option.label
		}));

	const securityObjectiveOptions: Option[] = filterDuplicateLabels(
		securityObjectiveScaleMap.map(createOption)
	);
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
<TextField
	{form}
	field="reference_link"
	label={m.link()}
	helpText={m.linkHelpText()}
	cacheLock={cacheLocks['reference_link']}
	bind:cachedValue={formDataCache['reference_link']}
/>
<Dropdown
	open={false}
	style="hover:text-indigo-700"
	icon="fa-solid fa-shield-halved"
	header={m.securityObjectives()}
>
	<RadioGroupInput
		{form}
		label={m.confidentiality()}
		field="confidentiality"
		valuePath="security_objectives.objectives.confidentiality.value"
		options={securityObjectiveOptions}
	/>
	<RadioGroupInput
		{form}
		label={m.integrity()}
		field="integrity"
		valuePath="security_objectives.objectives.integrity.value"
		options={securityObjectiveOptions}
	/>
	<RadioGroupInput
		{form}
		label={m.availability()}
		field="availability"
		valuePath="security_objectives.objectives.availability.value"
		options={securityObjectiveOptions}
	/>
	<RadioGroupInput
		{form}
		label={m.proof()}
		field="proof"
		valuePath="security_objectives.objectives.proof.value"
		options={securityObjectiveOptions}
	/>
	<RadioGroupInput
		{form}
		label={m.authenticity()}
		valuePath="security_objectives.objectives.authenticity.value"
		field="authenticity"
		options={securityObjectiveOptions}
	/>
	<RadioGroupInput
		{form}
		label={m.privacy()}
		field="privacy"
		valuePath="security_objectives.objectives.privacy.value"
		options={securityObjectiveOptions}
	/>
	<RadioGroupInput
		{form}
		label={m.safety()}
		field="safety"
		valuePath="security_objectives.objectives.safety.value"
		options={securityObjectiveOptions}
	/>
</Dropdown>
<Dropdown
	open={false}
	style="hover:text-indigo-700"
	icon="fa-regular fa-clock"
	header={m.disasterRecoveryObjectives()}
>
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
</Dropdown>
