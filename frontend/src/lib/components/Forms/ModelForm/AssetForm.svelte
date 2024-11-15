<script lang="ts">
	import { page } from '$app/stores';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import { SECURITY_OBJECTIVE_SCALE_MAP } from '$lib/utils/constants';
	import { getOptions } from '$lib/utils/crud';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import type { SuperValidated } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import RadioGroupInput from '../RadioGroupInput.svelte';
	import Select from '../Select.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { onMount } from 'svelte';

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

	async function fetchSecurityObjectives(): Promise<string[]> {
		const endpoint = '/assets/security-objectives/';
		const objectives = await fetch(endpoint).then((res) => res.json());
		return objectives;
	}

	let securityObjectives: string[] = [];

	onMount(async () => {
		securityObjectives = await fetchSecurityObjectives();
		console.log(securityObjectives);
	});

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
	style="hover:text-primary-700"
	icon="fa-solid fa-shield-halved"
	header={m.securityObjectives()}
>
	<div class="flex flex-col space-y-4">
		{#each securityObjectives as objective}
			<span class="flex flex-row items-center space-x-4">
				<Checkbox
					{form}
					field={objective}
					label={m.enabled()}
					valuePath="security_objectives.objectives.{objective}.is_enabled"
				/>
				<RadioGroupInput
					{form}
					label={safeTranslate(objective)}
					field={objective}
					valuePath="security_objectives.objectives.{objective}.value"
					options={securityObjectiveOptions}
					disabled={data.security_objectives?.objectives[objective]?.is_enabled === false}
				/></span
			>
		{/each}
	</div>
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
