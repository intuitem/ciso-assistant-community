<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import Checkbox from '../Checkbox.svelte';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		duplicate?: boolean;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>; // export let context: string = 'default';
	}

	let {
		form,
		model,
		duplicate = false,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	let riskToleranceChoices = $state<{ label: string; value: string }[]>([]);

	let isLocked = $derived(form.data?.is_locked || object?.is_locked || false);

	async function handleRiskMatrixChange(id: string) {
		riskToleranceChoices = [];

		if (id) {
			try {
				const response = await fetch(`/risk-matrices/${id}`);
				if (response.ok) {
					const data = await response.json();

					const riskMatrix =
						data.results && data.results.length > 0
							? data.results.find((item) => item.id === id)
							: null;

					if (riskMatrix && riskMatrix.json_definition) {
						const jsonDefinition = JSON.parse(riskMatrix.json_definition);
						const riskLevels = jsonDefinition.risk || [];
						riskToleranceChoices = riskLevels.map((level, index) => ({
							label: level.name,
							value: level.id ?? index
						}));
					}
				}
			} catch (error) {
				console.error('Error fetching risk matrix data:', error);
				riskToleranceChoices = [];
			}
		}
	}
</script>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="perimeters"
	optionsExtraFields={[['folder', 'str']]}
	field="perimeter"
	cacheLock={cacheLocks['perimeter']}
	bind:cachedValue={formDataCache['perimeter']}
	label={m.perimeter()}
	hidden={initialData.perimeter}
/>
<TextField
	{form}
	field="version"
	label={m.version()}
	cacheLock={cacheLocks['version']}
	bind:cachedValue={formDataCache['version']}
/>
{#if !duplicate}
	<Select
		{form}
		options={model.selectOptions['status']}
		translateOptions={false}
		field="status"
		hide
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<AutocompleteSelect
		{form}
		disabled={object.id || isLocked}
		translateOptions={false}
		disableDoubleDash
		optionsEndpoint="risk-matrices"
		field="risk_matrix"
		cacheLock={cacheLocks['risk_matrix']}
		bind:cachedValue={formDataCache['risk_matrix']}
		label={m.riskMatrix()}
		helpText={m.riskAssessmentMatrixHelpText()}
		hidden={initialData.risk_matrix}
		onChange={async (e) => await handleRiskMatrixChange(e)}
		mount={async (e) => await handleRiskMatrixChange(e)}
	/>
	{#if riskToleranceChoices.length > 0}
		<Select
			{form}
			translateOptions={false}
			options={riskToleranceChoices}
			field="risk_tolerance"
			cacheLock={cacheLocks['risk_tolerance']}
			bind:cachedValue={formDataCache['risk_tolerance']}
			label={m.riskTolerance()}
			helpText={m.riskToleranceHelpText()}
		/>
	{/if}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="users?is_third_party=false"
		optionsLabelField="email"
		field="authors"
		cacheLock={cacheLocks['authors']}
		bind:cachedValue={formDataCache['authors']}
		label={m.authors()}
	/>
	<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="users?is_third_party=false"
			optionsLabelField="email"
			field="reviewers"
			cacheLock={cacheLocks['reviewers']}
			bind:cachedValue={formDataCache['reviewers']}
			label={m.reviewers()}
		/>
		<TextField
			type="date"
			{form}
			field="eta"
			label={m.eta()}
			helpText={m.etaHelpText()}
			cacheLock={cacheLocks['eta']}
			bind:cachedValue={formDataCache['eta']}
		/>
		<TextField
			type="date"
			{form}
			field="due_date"
			label={m.dueDate()}
			helpText={m.dueDateHelpText()}
			cacheLock={cacheLocks['due_date']}
			bind:cachedValue={formDataCache['due_date']}
		/>
		<MarkdownField
			{form}
			field="observation"
			label={m.observation()}
			cacheLock={cacheLocks['observation']}
			bind:cachedValue={formDataCache['observation']}
		/>
		<Checkbox
			{form}
			field="is_locked"
			label={m.isLocked()}
			helpText={m.isLockedHelpText()}
			cacheLock={cacheLocks['is_locked']}
			bind:cachedValue={formDataCache['is_locked']}
		/>
	</Dropdown>
	{#if initialData.ebios_rm_study}
		<AutocompleteSelect
			{form}
			field="ebios_rm_study"
			cacheLock={cacheLocks['ebios_rm_study']}
			bind:cachedValue={formDataCache['ebios_rm_study']}
			label={m.ebiosRmStudy()}
			hidden
		/>
	{/if}
{/if}
