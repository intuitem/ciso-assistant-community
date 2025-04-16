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

	const { value: is_recurrent } = formFieldProxy(form, 'is_recurrent');
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
{#if !$is_recurrent}
	<TextField
		type="date"
		{form}
		field="task_date"
		label={m.date()}
		cacheLock={cacheLocks['task_date']}
		bind:cachedValue={formDataCache['task_date']}
	/>
{/if}
<Checkbox
	{form}
	field="is_recurrent"
	label={m.recurrent()}
	helpText={m.isRecurrentHelpText()}
	cacheLock={cacheLocks['is_recurrent']}
	bind:cachedValue={formDataCache['is_recurrent']}
/>
{#if $is_recurrent}
	<Dropdown
		open={true}
		style="hover:text-primary-700"
		icon="fa-solid fa-calendar-days"
		header={m.schedule()}
	>
		<TextField
			type="date"
			{form}
			field="task_date"
			label={m.startDate()}
			cacheLock={cacheLocks['task_date']}
			bind:cachedValue={formDataCache['task_date']}
		/>
		<div class="flex w-full items-center space-x-3">
			<span class="mt-5 font-semibold text-sm text-gray-800">{m.each()}</span>
			<NumberField
				{form}
				field="interval"
				valuePath="schedule.interval"
				label={m.interval()}
				cacheLock={cacheLocks['interval']}
				bind:cachedValue={formDataCache['interval']}
			/>
			<Select
				{form}
				field="frequency"
				valuePath="schedule.frequency"
				disableDoubleDash={true}
				options={[
					{ value: 'DAILY', label: m.day() },
					{ value: 'WEEKLY', label: m.week() },
					{ value: 'MONTHLY', label: m.month() },
					{ value: 'YEARLY', label: m.year() }
				]}
				cacheLock={cacheLocks['frequency']}
				bind:cachedValue={formDataCache['frequency']}
				label={m.frequency()}
			/>
		</div>
		<div class="flex w-full items-center space-x-3">
			{#if $frequency == 'MONTHLY' || $frequency == 'YEARLY'}
				<span class="mt-5 font-semibold text-sm text-gray-800">{m.the()}</span>
				<AutocompleteSelect
					{form}
					multiple
					baseClass="w-full"
					translateOptions={false}
					field="weeks_of_month"
					valuePath="schedule.weeks_of_month"
					disableDoubleDash={true}
					options={[
						{ value: 1, label: m.first() },
						{ value: 2, label: m.second() },
						{ value: 3, label: m.third() },
						{ value: 4, label: m.fourth() },
						{ value: -1, label: m.last() }
					]}
					cacheLock={cacheLocks['weeks_of_month']}
					bind:cachedValue={formDataCache['weeks_of_month']}
					label={m.weeks()}
				/>
			{/if}
			{#if $frequency == 'WEEKLY' || $frequency == 'MONTHLY' || $frequency == 'YEARLY'}
				<AutocompleteSelect
					{form}
					multiple
					baseClass="w-full"
					translateOptions={false}
					field="days_of_week"
					valuePath="schedule.days_of_week"
					disableDoubleDash={true}
					options={[
						{ value: 1, label: m.monday() },
						{ value: 2, label: m.tuesday() },
						{ value: 3, label: m.wednesday() },
						{ value: 4, label: m.thursday() },
						{ value: 5, label: m.friday() },
						{ value: 6, label: m.saturday() },
						{ value: 7, label: m.sunday() }
					]}
					cacheLock={cacheLocks['days_of_week']}
					bind:cachedValue={formDataCache['days_of_week']}
					label={m.days()}
				/>
			{/if}
		</div>
		{#if $frequency == 'YEARLY'}
			<div class="flex w-full items-center space-x-3">
				<span class="mt-5 font-semibold text-sm text-gray-800">{m.of()}</span>
				<AutocompleteSelect
					{form}
					multiple
					translateOptions={false}
					field="months_of_year"
					valuePath="schedule.months_of_year"
					disableDoubleDash={true}
					options={[
						{ value: 1, label: m.january() },
						{ value: 2, label: m.february() },
						{ value: 3, label: m.march() },
						{ value: 4, label: m.april() },
						{ value: 5, label: m.may() },
						{ value: 6, label: m.june() },
						{ value: 7, label: m.july() },
						{ value: 8, label: m.august() },
						{ value: 9, label: m.september() },
						{ value: 10, label: m.october() },
						{ value: 11, label: m.november() },
						{ value: 12, label: m.december() }
					]}
					cacheLock={cacheLocks['months_of_year']}
					bind:cachedValue={formDataCache['months_of_year']}
					label={m.month()}
				/>
			</div>
		{/if}
		<TextField
			type="date"
			{form}
			field="end_date"
			valuePath="schedule.end_date"
			label={m.endDate()}
			cacheLock={cacheLocks['end_date']}
			bind:cachedValue={formDataCache['end_date']}
		/>
	</Dropdown>
{/if}
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
<Checkbox {form} field="enabled" label={m.enabled()} />
