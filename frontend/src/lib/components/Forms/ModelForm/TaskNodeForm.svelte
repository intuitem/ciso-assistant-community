<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import { formFieldProxy } from 'sveltekit-superforms';
	import NumberField from '../NumberField.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};

	const { value: is_template } = formFieldProxy(form, 'is_template');
	const { value: frequency } = formFieldProxy(form, 'schedule.frequency');
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<TextField
	type="date"
	{form}
	field="task_date"
	label={m.date()}
	cacheLock={cacheLocks['task_date']}
	bind:cachedValue={formDataCache['task_date']}
/>
<Checkbox
	{form}
	field="is_template"
	label={m.isRecurrent()}
	helpText={m.isRecurrentHelpText()}
	cacheLock={cacheLocks['is_template']}
	bind:cachedValue={formDataCache['is_template']}
/>
{#if $is_template}
	<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
		<NumberField
			{form}
			field="interval"
			valuePath="schedule.interval"
			label={m.interval()}
			helpText={m.intervalHelpText()}
			cacheLock={cacheLocks['interval']}
			bind:cachedValue={formDataCache['interval']}
		/>
		<Select
			{form}
			field="frequency"
			valuePath="schedule.frequency"
			disableDoubleDash={true}
			options={[
				{ value: 'DAILY', label: 'day' },
				{ value: 'WEEKLY', label: 'week' },
				{ value: 'MONTHLY', label: 'month' },
				{ value: 'YEARLY', label: 'year' }
			]}
			cacheLock={cacheLocks['frequency']}
			bind:cachedValue={formDataCache['frequency']}
			label={m.frequency()}
		/>
		{#if $frequency == 'MONTHLY' || $frequency == 'YEARLY'}
			<AutocompleteSelect
				{form}
				multiple
				translateOptions={false}
				field="weeks_of_month"
				valuePath="schedule.weeks_of_month"
				disableDoubleDash={true}
				options={[
					{ value: 1, label: 'First' },
					{ value: 2, label: 'Second' },
					{ value: 3, label: 'Third' },
					{ value: 4, label: 'Fourth' },
					{ value: -1, label: 'Last' }
				]}
				cacheLock={cacheLocks['weeks_of_month']}
				bind:cachedValue={formDataCache['weeks_of_month']}
				label={'weeks'}
			/>
		{/if}
		{#if $frequency == 'WEEKLY' || $frequency == 'MONTHLY' || $frequency == 'YEARLY'}
			<AutocompleteSelect
				{form}
				multiple
				translateOptions={false}
				field="days_of_week"
				valuePath="schedule.days_of_week"
				disableDoubleDash={true}
				options={[
					{ value: 1, label: 'Monday' },
					{ value: 2, label: 'Tuesday' },
					{ value: 3, label: 'Wednesday' },
					{ value: 4, label: 'Thursday' },
					{ value: 5, label: 'Friday' },
					{ value: 6, label: 'Saturday' },
					{ value: 0, label: 'Sunday' }
				]}
				cacheLock={cacheLocks['days_of_week']}
				bind:cachedValue={formDataCache['days_of_week']}
				label={'days'}
			/>
		{/if}
		{#if $frequency == 'YEARLY'}
			<AutocompleteSelect
				{form}
				multiple
				translateOptions={false}
				field="months_of_year"
				valuePath="schedule.months_of_year"
				disableDoubleDash={true}
				options={[
					{ value: 1, label: 'January' },
					{ value: 2, label: 'February' },
					{ value: 3, label: 'March' },
					{ value: 4, label: 'April' },
					{ value: 5, label: 'May' },
					{ value: 6, label: 'June' },
					{ value: 7, label: 'July' },
					{ value: 8, label: 'August' },
					{ value: 9, label: 'September' },
					{ value: 10, label: 'October' },
					{ value: 11, label: 'November' },
					{ value: 12, label: 'December' }
				]}
				cacheLock={cacheLocks['months_of_year']}
				bind:cachedValue={formDataCache['months_of_year']}
				label={'month'}
			/>
		{/if}
		<TextField
			type="date"
			{form}
			field="end_date"
			valuePath="schedule.end_date"
			label={'end date'}
			cacheLock={cacheLocks['end_date']}
			bind:cachedValue={formDataCache['end_date']}
		/>
	</Dropdown>
{/if}
<TextField
	type="date"
	{form}
	field="eta_or_completion_date"
	label={m.completionDate()}
	helpText={m.completionDateHelpText()}
	cacheLock={cacheLocks['eta_or_completion_date']}
	bind:cachedValue={formDataCache['eta_or_completion_date']}
/>
<TextField
	type="date"
	{form}
	field="due_date"
	label={m.dueDate()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="assigned_to"
	cacheLock={cacheLocks['assigned_to']}
	bind:cachedValue={formDataCache['assigned_to']}
	label={m.assignedTo()}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<Select
		{form}
		field="status"
		disableDoubleDash={true}
		options={model.selectOptions['status']}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
		label={m.status()}
	/>
	<TextField
		{form}
		field="ref_id"
		label={m.refId()}
		cacheLock={cacheLocks['ref_id']}
		bind:cachedValue={formDataCache['ref_id']}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="assets"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="assets"
		label={m.assets()}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="applied-controls"
		optionsExtraFields={[['folder', 'str']]}
		field="applied_controls"
		label={m.appliedControls()}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="compliance-assessments"
		field="compliance_assessments"
		cacheLock={cacheLocks['compliance_assessments']}
		bind:cachedValue={formDataCache['compliance_assessments']}
		label={m.complianceAssessments()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="risk-assessments"
		optionsExtraFields={[['perimeter', 'str']]}
		optionsLabelField="str"
		field="risk_assessment"
		cacheLock={cacheLocks['risk_assessment']}
		bind:cachedValue={formDataCache['risk_assessment']}
		label={m.riskAssessments()}
	/>
</Dropdown>
<TextArea
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
<Checkbox {form} field="enabled" label={m.enabled()} />
