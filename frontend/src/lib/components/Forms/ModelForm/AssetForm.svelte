<script lang="ts">
	import { page } from '$app/state';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { SECURITY_OBJECTIVE_SCALE_MAP } from '$lib/utils/constants';

	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { onMount } from 'svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Duration from '../Duration.svelte';
	import RadioGroup from '../RadioGroup.svelte';
	import Select from '../Select.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
		data?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		data = {}
	}: Props = $props();

	type SecurityObjectiveScale = '0-3' | '1-4' | 'FIPS-199';
	const scale: SecurityObjectiveScale = page.data.settings.security_objective_scale;
	const securityObjectiveScaleMap = SECURITY_OBJECTIVE_SCALE_MAP[scale];
	const reducedSecurityObjectiveMap = securityObjectiveScaleMap.filter(
		(label, index) => !securityObjectiveScaleMap.slice(0, index).includes(label)
	);

	async function fetchSecurityObjectives(): Promise<string[]> {
		const endpoint = '/assets/security-objectives/';
		const objectives = await fetch(endpoint).then((res) => res.json());
		return objectives;
	}

	async function fetchDisasterRecoveryObjectives() {
		const endpoint = '/assets/disaster-recovery-objectives/';
		const objectives = await fetch(endpoint).then((res) => res.json());
		return objectives;
	}

	let securityObjectives: string[] = $state([]);
	let disasterRecoveryObjectives: string[] = $state([]);

	onMount(async () => {
		securityObjectives = await fetchSecurityObjectives();
		disasterRecoveryObjectives = await fetchDisasterRecoveryObjectives();
	});

	interface Option {
		label: string;
		value: number;
		suggested?: boolean;
	}

	const createOption = (label: string): Option => ({
		label,
		value: securityObjectiveScaleMap.findIndex((_label) => label === _label)
	});

	const securityObjectiveOptions: Option[] = reducedSecurityObjectiveMap.map(createOption);

	// Dynamic configuration based on asset type
	const typeConfig = $derived.by(() => {
		if (data.type === 'PR') {
			return {
				securityKey: 'security_objectives',
				recoveryKey: 'disaster_recovery_objectives',
				securityLabel: m.securityObjectives(),
				recoveryLabel: m.disasterRecoveryObjectives()
			};
		} else if (data.type === 'SP') {
			return {
				securityKey: 'security_capabilities',
				recoveryKey: 'recovery_capabilities',
				securityLabel: m.securityCapabilities(),
				recoveryLabel: m.recoveryCapabilities()
			};
		}
		return null;
	});
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="asset-class"
	optionsLabelField="full_path"
	field="asset_class"
	cacheLock={cacheLocks['asset_class']}
	bind:cachedValue={formDataCache['asset_class']}
	label={m.assetClass()}
/>
<TextField
	{form}
	field="ref_id"
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
	label={m.refId()}
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors?user__is_third_party=False"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	label={m.owner()}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	pathField="path"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<Select
	{form}
	options={model.selectOptions['type']}
	disableDoubleDash={true}
	field="type"
	label="Type"
	cacheLock={cacheLocks['type']}
	bind:cachedValue={formDataCache['type']}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="assets"
	optionsInfoFields={{
		fields: [
			{
				field: 'type'
			}
		],
		classes: 'text-blue-500'
	}}
	optionsDetailedUrlParameters={[['exclude_children', object.id]]}
	optionsLabelField="auto"
	pathField="path"
	optionsSelf={object}
	field="parent_assets"
	cacheLock={cacheLocks['parent_assets']}
	bind:cachedValue={formDataCache['parent_assets']}
	label={m.parentAssets()}
	helpText={m.supportedAssetsHelpText()}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="assets"
	optionsInfoFields={{
		fields: [
			{
				field: 'type'
			}
		],
		classes: 'text-blue-500'
	}}
	optionsDetailedUrlParameters={[['exclude_parents', object.id]]}
	optionsLabelField="auto"
	pathField="path"
	optionsSelf={object}
	field="support_assets"
	cacheLock={cacheLocks['support_assets']}
	bind:cachedValue={formDataCache['support_assets']}
	label={m.supportAssets()}
	helpText={m.supportingAssetsHelpText()}
/>
{#if typeConfig}
	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-shield-halved"
		header={typeConfig.securityLabel}
	>
		<div class="flex flex-col space-y-4">
			{#each securityObjectives as objective}
				<span class="flex flex-row items-end space-x-4">
					<Checkbox
						{form}
						field={objective}
						label={''}
						valuePath="{typeConfig.securityKey}.objectives.{objective}.is_enabled"
						checkboxComponent="switch"
						class="h-full flex flex-row items-center justify-center my-1"
						classesContainer="h-full"
					/>
					<RadioGroup
						possibleOptions={securityObjectiveOptions}
						{form}
						label={safeTranslate(objective)}
						labelKey="label"
						key="value"
						field={objective}
						valuePath="{typeConfig.securityKey}.objectives.{objective}.value"
						disabled={data[typeConfig.securityKey]?.objectives?.[objective]?.is_enabled === false}
					/>
				</span>
			{/each}
		</div>
	</Dropdown>
	<Dropdown
		open={false}
		style="hover:text-indigo-700"
		icon="fa-regular fa-clock"
		header={typeConfig.recoveryLabel}
	>
		<div class="flex flex-col space-y-4">
			{#each disasterRecoveryObjectives as objective}
				<Duration
					{form}
					field={objective}
					label={safeTranslate(objective)}
					helpText={Object.hasOwn(m, `${objective}HelpText`) ? m[`${objective}HelpText`]() : ''}
					valuePath="{typeConfig.recoveryKey}.objectives.{objective}.value"
				/>
			{/each}
		</div>
	</Dropdown>
{/if}
{#if data.type === 'PR'}
	<Dropdown
		open={false}
		style="hover:text-purple-700"
		icon="fa-solid fa-building-columns"
		header={m.doraSpecific()}
	>
		<Checkbox
			{form}
			field="is_business_function"
			label={m.isBusinessFunction()}
			cacheLock={cacheLocks['is_business_function']}
			bind:cachedValue={formDataCache['is_business_function']}
		/>
		<Select
			{form}
			options={model.selectOptions['dora_licenced_activity']}
			field="dora_licenced_activity"
			label={m.doraLicencedActivity()}
			cacheLock={cacheLocks['dora_licenced_activity']}
			bind:cachedValue={formDataCache['dora_licenced_activity']}
		/>
		<Select
			{form}
			options={model.selectOptions['dora_criticality_assessment']}
			field="dora_criticality_assessment"
			label={m.doraCriticalityAssessment()}
			cacheLock={cacheLocks['dora_criticality_assessment']}
			bind:cachedValue={formDataCache['dora_criticality_assessment']}
			disableDoubleDash={true}
		/>
		<TextField
			{form}
			field="dora_criticality_justification"
			label={m.doraCriticalityJustification()}
			cacheLock={cacheLocks['dora_criticality_justification']}
			bind:cachedValue={formDataCache['dora_criticality_justification']}
		/>
		<Select
			{form}
			options={model.selectOptions['dora_discontinuing_impact']}
			field="dora_discontinuing_impact"
			label={m.doraDiscontinuingImpact()}
			cacheLock={cacheLocks['dora_discontinuing_impact']}
			bind:cachedValue={formDataCache['dora_discontinuing_impact']}
			disableDoubleDash={true}
		/>
	</Dropdown>
{/if}
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<TextField
		{form}
		field="reference_link"
		label={m.link()}
		helpText={m.linkHelpText()}
		cacheLock={cacheLocks['reference_link']}
		bind:cachedValue={formDataCache['reference_link']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="applied-controls"
		optionsLabelField="auto"
		field="applied_controls"
		cacheLock={cacheLocks['applied_controls']}
		bind:cachedValue={formDataCache['applied_controls']}
		label={m.appliedControls()}
		helpText={m.appliedControlsLinkedToAssetHelpText()}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="security-exceptions"
		optionsLabelField="auto"
		field="security_exceptions"
		cacheLock={cacheLocks['security_exceptions']}
		bind:cachedValue={formDataCache['security_exceptions']}
		label={m.securityExceptions()}
	/>
	{#if data.type === 'SP'}
		<AutocompleteSelect
			multiple
			{form}
			optionsEndpoint="asset-capabilities"
			field="overridden_children_capabilities"
			cacheLock={cacheLocks['overridden_children_capabilities']}
			bind:cachedValue={formDataCache['overridden_children_capabilities']}
			label={m.overriddenChildrenCapabilities()}
			helpText={m.overriddenChildrenCapabilitiesHelpText()}
		/>
	{/if}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="solutions"
		optionsLabelField="auto"
		optionsExtraFields={[['provider_entity', 'str']]}
		field="solutions"
		cacheLock={cacheLocks['solutions']}
		bind:cachedValue={formDataCache['solutions']}
		label={m.solutions()}
		helpText={m.solutionsLinkedToAssetHelpText()}
	/>
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		helpText={m.observationHelpText()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	<AutocompleteSelect
		multiple
		{form}
		createFromSelection={true}
		optionsEndpoint="filtering-labels"
		optionsLabelField="label"
		field="filtering_labels"
		helpText={m.labelsHelpText()}
		label={m.labels()}
		translateOptions={false}
		allowUserOptions="append"
	/>
</Dropdown>
{#if initialData.ebios_rm_studies}
	<AutocompleteSelect
		{form}
		field="ebios_rm_studies"
		multiple
		cacheLock={cacheLocks['ebios_rm_studies']}
		bind:cachedValue={formDataCache['ebios_rm_studies']}
		label={m.ebiosRmStudies()}
		hidden
	/>
{/if}
