<script lang="ts">
	import { page } from '$app/stores';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { SECURITY_OBJECTIVE_SCALE_MAP } from '$lib/utils/constants';
	import { getOptions } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import { onMount } from 'svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Duration from '../Duration.svelte';
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

	let securityObjectives: string[] = [];
	let disasterRecoveryObjectives: string[] = [];

	onMount(async () => {
		securityObjectives = await fetchSecurityObjectives();
		disasterRecoveryObjectives = await fetchDisasterRecoveryObjectives();
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

<AutocompleteSelect
	{form}
	multiple
	options={getOptions({ objects: model.foreignKeys['owner'], label: 'email' })}
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	label={m.owner()}
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
	hidden={data.type === 'PR'}
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
{#if data.type === 'PR'}
	<Dropdown
		open={false}
		style="hover:text-primary-700"
		icon="fa-solid fa-shield-halved"
		header={m.securityObjectives()}
	>
		<div class="flex flex-col space-y-4">
			{#each securityObjectives as objective}
				{@const objectiveFormData =
					data.security_objectives?.objectives &&
					Object.hasOwn(data.security_objectives?.objectives, objective)
						? data.security_objectives.objectives[objective]
						: {}}
				<span class="flex flex-row items-end space-x-4">
					<Checkbox
						{form}
						field={objective}
						label={''}
						valuePath="security_objectives.objectives.{objective}.is_enabled"
						checkboxComponent="switch"
						class="h-full flex flex-row items-center justify-center my-1"
						classesContainer="h-full"
					/>
					<RadioGroupInput
						{form}
						label={safeTranslate(objective)}
						field={objective}
						valuePath="security_objectives.objectives.{objective}.value"
						options={securityObjectiveOptions}
						disabled={objectiveFormData && objectiveFormData.is_enabled === false}
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
		<div class="flex flex-col space-y-4">
			{#each disasterRecoveryObjectives as objective}
				<Duration
					{form}
					field={objective}
					label={safeTranslate(objective)}
					helpText={Object.hasOwn(m, `${objective}HelpText`) ? m[`${objective}HelpText`]() : ''}
					valuePath="disaster_recovery_objectives.objectives.{objective}.value"
				/>
			{/each}
		</div>
	</Dropdown>
{/if}
<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	options={getOptions({ objects: model.foreignKeys['filtering_labels'], label: 'label' })}
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>
{#if initialData.ebios_rm_studies}
	<AutocompleteSelect
		{form}
		field="ebios_rm_studies"
		multiple
		cacheLock={cacheLocks['ebios_rm_studies']}
		bind:cachedValue={formDataCache['ebios_rm_studies']}
		label={m.ebiosRmStudies()}
		options={getOptions({ objects: model.foreignKeys['ebios_rm_studies'] })}
		hidden
	/>
{/if}
