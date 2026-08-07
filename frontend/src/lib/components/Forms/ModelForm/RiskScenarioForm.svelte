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
	import { safeTranslate } from '$lib/utils/i18n';

	import TextField from '$lib/components/Forms/TextField.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
		context?: string;
		updated_fields?: Set<string>;
		[key: string]: any;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		updated_fields = new Set(),
		object,
		context = 'default',
		...rest
	}: Props = $props();

	let isParentLocked = $derived(object?.risk_assessment?.is_locked || false);

	async function fetchDefaultRefId(riskAssessmentId: string) {
		try {
			const response = await fetch(
				`/risk-scenarios/default-ref-id/?risk_assessment=${riskAssessmentId}`
			);
			const result = await response.json();
			if (response.ok && result.results) {
				form.form.update((currentData) => {
					updated_fields.add('ref_id');
					return { ...currentData, ref_id: result.results };
				});
			} else {
				console.error(result.error || 'Failed to fetch default ref_id');
			}
		} catch (error) {
			console.error('Error fetching default ref_id:', error);
		}
	}

	const scopeFolder = $derived(rest?.scopeFolder || { id: '' });
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
						folder: scopeFolder?.id || initialData?.folder,
						...(object?.id ? { risk_scenarios: [object.id] } : {})
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
	optionsEndpoint="risk-assessments"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="str"
	field="risk_assessment"
	cacheLock={cacheLocks['risk_assessment']}
	bind:cachedValue={formDataCache['risk_assessment']}
	label={m.riskAssessment()}
	helpText={m.riskAssessmentHelpText()}
	hidden={initialData.risk_assessment}
	onChange={async (e) => {
		if (e) {
			await fetchDefaultRefId(e);
		}
	}}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="assets"
	lazy
	optionsExtraFields={[['folder', 'str']]}
	optionsDetailedUrlParameters={[
		scopeFolder?.id ? ['scope_folder_id', scopeFolder.id] : ['', undefined]
	]}
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
	optionsEndpoint="terminologies?field_path=ro_to.risk_origin&is_visible=true"
	optionsLabelField="translated_name"
	field="risk_origin"
	cacheLock={cacheLocks['risk_origin']}
	bind:cachedValue={formDataCache['risk_origin']}
	label={m.riskOrigin()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="threats"
	optionsExtraFields={[['folder', 'str']]}
	optionsDetailedUrlParameters={[
		scopeFolder?.id ? ['scope_folder_id', scopeFolder.id] : ['', undefined]
	]}
	optionsLabelField="auto"
	field="threats"
	cacheLock={cacheLocks['threats']}
	bind:cachedValue={formDataCache['threats']}
	label={m.threats()}
/>
{#if $page.data.featureflags?.threat_modeling}
	<div class="flex flex-row space-x-2 items-center">
		<div class="w-full">
			<AutocompleteSelect
				{form}
				nullable
				optionsEndpoint="threat-models"
				optionsExtraFields={[['folder', 'str']]}
				optionsDetailedUrlParameters={[
					scopeFolder?.id ? ['scope_folder_id', scopeFolder.id] : ['', undefined]
				]}
				optionsLabelField="auto"
				field="threat_models"
				cacheLock={cacheLocks['threat_models']}
				bind:cachedValue={formDataCache['threat_models']}
				label={m.threatModel()}
			/>
		</div>
		{#if context !== 'create'}
			<div class="mt-4">
				<button
					class="btn preset-tonal-primary h-10 w-10"
					onclick={() => modalThreatModelCreateForm()}
					type="button"
					title={safeTranslate('add-' + threatModelModel.localName)}
					aria-label={safeTranslate('add-' + threatModelModel.localName)}
				>
					<i class="fa-solid fa-plus text-sm"></i>
				</button>
			</div>
		{/if}
	</div>
{/if}
