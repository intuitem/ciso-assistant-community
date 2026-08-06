<script lang="ts">
	import { page } from '$app/stores';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { type ModalComponent, type ModalSettings } from '@skeletonlabs/skeleton-svelte';
	import { getModelInfo } from '$lib/utils/crud';
	import { ThreatModelSchema } from '$lib/utils/schemas';
	import { defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { invalidateAll } from '$app/navigation';

	import Select from '../Select.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { run } from 'svelte/legacy';

	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	// Convert priority values from strings to integers for proper schema validation
	run(() => {
		if (model?.selectOptions?.priority) {
			model.selectOptions.priority.forEach((element) => {
				element.value = parseInt(element.value);
			});
		}
	});
	const modalStore: ModalStore = getModalStore();

	const threatModelModel = getModelInfo('threat-models');

	function modalThreatModelCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				// created already linked when the scenario exists; on create the user
				// picks it from the refreshed list
				form: defaults(
					{
						folder: $page.data?.scenario?.folder?.id ?? initialData?.folder,
						...(object?.id ? { quantitative_risk_scenarios: [object.id] } : {})
					},
					zod(ThreatModelSchema)
				),
				formAction: '/threat-models?/create',
				model: threatModelModel,
				debug: false
			}
		};
		modalStore.trigger({
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add-' + threatModelModel.localName),
			response: (r: boolean) => {
				if (r) invalidateAll();
			}
		});
	}
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="quantitative-risk-studies"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="quantitative_risk_study"
	cacheLock={cacheLocks['quantitative_risk_study']}
	bind:cachedValue={formDataCache['quantitative_risk_study']}
	label="Quantitative Risk Study"
	helpText={m.quantitativeRiskStudyHelpText()}
	hidden={initialData.quantitative_risk_study}
/>

<Checkbox {form} field="is_selected" label={m.isSelected()} helpText={m.isSelectedHelpText()} />
<AutocompleteSelect
	{form}
	multiple
	lazy
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	optionsInfoFields={{
		fields: [
			{
				field: 'type'
			}
		],
		classes: 'text-blue-500'
	}}
	optionsLabelField="auto"
	field="assets"
	cacheLock={cacheLocks['assets']}
	bind:cachedValue={formDataCache['assets']}
	label={m.assets()}
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="threats?exclude_legacy_ttp=true"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="threats"
	cacheLock={cacheLocks['threats']}
	bind:cachedValue={formDataCache['threats']}
	label={m.threats()}
/>

{#if $page.data.featureflags?.threat_modeling}
	<div class="flex items-center gap-2">
		<div class="flex-1">
			<AutocompleteSelect
				{form}
				nullable
				optionsEndpoint="threat-models"
				optionsExtraFields={[['folder', 'str']]}
				optionsLabelField="auto"
				field="threat_models"
				cacheLock={cacheLocks['threat_models']}
				bind:cachedValue={formDataCache['threat_models']}
				label={m.threatModel()}
			/>
		</div>
		<button
			class="btn preset-tonal-primary shrink-0 h-10 w-10"
			onclick={() => modalThreatModelCreateForm()}
			type="button"
			title={safeTranslate('add-' + threatModelModel.localName)}
			aria-label={safeTranslate('add-' + threatModelModel.localName)}
		>
			<i class="fa-solid fa-plus text-sm"></i>
		</button>
	</div>
{/if}

<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<Select
		{form}
		options={model.selectOptions['priority']}
		field="priority"
		label={m.priority()}
		helpText={m.quantRiskPriorityHelpText()}
		cacheLock={cacheLocks['priority']}
		bind:cachedValue={formDataCache['priority']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		lazy
		optionsEndpoint="vulnerabilities"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="vulnerabilities"
		cacheLock={cacheLocks['vulnerabilities']}
		bind:cachedValue={formDataCache['vulnerabilities']}
		label={m.vulnerabilities()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="terminologies?field_path=qualifications&is_visible=true"
		optionsLabelField="translated_name"
		field="qualifications"
		cacheLock={cacheLocks['qualifications']}
		bind:cachedValue={formDataCache['qualifications']}
		label={safeTranslate('qualifications')}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="actors"
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
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
</Dropdown>
