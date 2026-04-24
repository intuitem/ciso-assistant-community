<script lang="ts">
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import { m } from '$paraglide/messages';
	import TextArea from '../TextArea.svelte';
	import Checkbox from '../Checkbox.svelte';
	import RadioGroup from '../RadioGroup.svelte';
	import { type ModalComponent, type ModalSettings } from '@skeletonlabs/skeleton-svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { page } from '$app/state';
	import { safeTranslate } from '$lib/utils/i18n';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';

	interface Props {
		form: SuperForm<Record<string, any>>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context?: 'create' | 'edit';
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context = 'create'
	}: Props = $props();

	const formData = form.form;

	const modalStore: ModalStore = getModalStore();

	function modalMeasureCreateForm(): void {
		const measureModel = page.data.measureModel;
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: page.data.measureCreateForm,
				formAction: '?/createAppliedControl',
				model: measureModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + measureModel.localName)
		};
		modalStore.trigger(modal);
	}

	const activityBackground = context === 'edit' ? 'bg-white' : 'bg-surface-100-900';
	const activeActivity: string = page.url.searchParams.get('activity') || '';

	const getCriticality = (
		dependency: number,
		penetration: number,
		maturity: number,
		trust: number
	) => {
		if (maturity === 0 || trust === 0) return 0;
		return ((dependency * penetration) / (maturity * trust)).toFixed(2).replace(/\.?0+$/, '');
	};

	let currentCriticality = $derived(
		getCriticality(
			$formData.current_dependency,
			$formData.current_penetration,
			$formData.current_maturity,
			$formData.current_trust
		)
	);

	let residualCriticality = $derived(
		getCriticality(
			$formData.residual_dependency,
			$formData.residual_penetration,
			$formData.residual_maturity,
			$formData.residual_trust
		)
	);

	// Track selected entity option from autocomplete (with all fields included)
	let selectedEntityOption: any[] = $state([]);

	// Auto-fill the entity label, relationship category, and default assessment fields when a
	// third-party entity is selected.
	$effect(() => {
		if (selectedEntityOption.length > 0) {
			const entity = selectedEntityOption[0];
			if (context != 'edit') {
				$formData.entity_name = entity.name ?? entity.str ?? $formData.entity_name;
			}
		}
	});
</script>

<FolderTreeSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.folder()}
	hidden
/>
<div
	class="relative p-2 space-y-2 rounded-container {activeActivity === 'one'
		? 'border-2 border-primary-500'
		: 'border-2 border-gray-300 border-dashed'}"
>
	<p
		class="absolute -top-3 {activityBackground} font-bold {activeActivity === 'one'
			? 'text-primary-500'
			: 'text-gray-500'}"
	>
		{m.activityOne()}
	</p>
	<div class="space-y-4">
		<div class="min-w-0 space-y-2">
			<div class="space-y-2">
				<AutocompleteSelect
					{form}
					optionsEndpoint="entities"
					field="third_party_entity"
					baseClass="w-full"
					cacheLock={cacheLocks['third_party_entity']}
					bind:cachedValue={formDataCache['third_party_entity']}
					bind:cachedOptions={selectedEntityOption}
					label={m.thirdPartyEntity()}
					helpText={m.thirdPartyEntityHelpText()}
					includeAllOptionFields={true}
					optionsInfoFields={{
						fields: [
							{
								field: 'relationship',
								display: (relationships) => {
									if (!relationships || relationships.length === 0) return '';
									return relationships.map((r) => safeTranslate(r.str || r.name || r)).join(' | ');
								}
							}
						],
						position: 'suffix',
						separator: ' | ',
						classes: 'text-xs text-surface-500'
					}}
				/>
				<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
					<TextField
						{form}
						field="entity_name"
						label={m.entity()}
						classesContainer="w-full"
						cacheLock={cacheLocks['entity_name']}
						bind:cachedValue={formDataCache['entity_name']}
					/>
					<AutocompleteSelect
						{form}
						optionsEndpoint="terminologies"
						optionsDetailedUrlParameters={[
							['field_path', 'entity.relationship'],
							['is_visible', 'true']
						]}
						field="category"
						label={m.category()}
						cacheLock={cacheLocks['category']}
						bind:cachedValue={formDataCache['category']}
						helpText={m.stakeholderCategoryHelpText()}
					/>
				</div>
				<Checkbox
					{form}
					field="is_selected"
					label={m.selected()}
					helpText={m.stakeholderIsSelectedHelpText()}
				/>
				<TextArea
					{form}
					field="justification"
					label={m.justification()}
					cacheLock={cacheLocks['justification']}
					bind:cachedValue={formDataCache['justification']}
				/>
			</div>

			<h4 class="h4 font-semibold self-start">{m.currentAssessment()}</h4>
			<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:space-x-4">
				<div class="flex flex-col space-y-4 w-fit items-center">
					<span class="flex flex-row flex-wrap items-center gap-4">
						<RadioGroup
							{form}
							possibleOptions={[
								{ label: '0', value: 0 },
								{ label: '1', value: 1 },
								{ label: '2', value: 2 },
								{ label: '3', value: 3 },
								{ label: '4', value: 4 }
							]}
							label={m.dependency()}
							field="current_dependency"
							labelKey="label"
							key="value"
							cacheLock={cacheLocks['current_dependency']}
							bind:cachedValue={formDataCache['current_dependency']}
							helpText={m.dependencyHelpText()}
						/>
						<i class="fa-solid fa-times"></i>
						<RadioGroup
							{form}
							possibleOptions={[
								{ label: '0', value: 0 },
								{ label: '1', value: 1 },
								{ label: '2', value: 2 },
								{ label: '3', value: 3 },
								{ label: '4', value: 4 }
							]}
							label={m.penetration()}
							field="current_penetration"
							labelKey="label"
							key="value"
							cacheLock={cacheLocks['current_penetration']}
							bind:cachedValue={formDataCache['current_penetration']}
							helpText={m.penetrationHelpText()}
						/>
					</span>

					<hr class="border-t-2! border-surface-900! self-stretch" />

					<span class="flex flex-row flex-wrap items-center gap-4">
						<RadioGroup
							{form}
							possibleOptions={[
								{ label: '1', value: 1 },
								{ label: '2', value: 2 },
								{ label: '3', value: 3 },
								{ label: '4', value: 4 }
							]}
							label={m.maturity()}
							field="current_maturity"
							labelKey="label"
							key="value"
							cacheLock={cacheLocks['current_maturity']}
							bind:cachedValue={formDataCache['current_maturity']}
							helpText={m.maturityHelpText()}
						/>
						<i class="fa-solid fa-times"></i>
						<RadioGroup
							{form}
							possibleOptions={[
								{ label: '1', value: 1 },
								{ label: '2', value: 2 },
								{ label: '3', value: 3 },
								{ label: '4', value: 4 }
							]}
							label={m.trust()}
							field="current_trust"
							labelKey="label"
							key="value"
							cacheLock={cacheLocks['current_trust']}
							bind:cachedValue={formDataCache['current_trust']}
							helpText={m.trustHelpText()}
						/></span
					>
				</div>
				<i class="fa-solid fa-equals self-center"></i>
				<div class="flex flex-col mb-5 w-fit">
					<label for="current_criticality" class="text-sm font-semibold">
						{m.criticality()}
					</label>
					<span class="chip text-base text-center px-4 py-1 rounded-base preset-filled">
						{currentCriticality}
					</span>
				</div>
			</div>
		</div>
	</div>
</div>

{#if context === 'edit'}
	<div
		class="relative p-2 space-y-2 rounded-container {activeActivity === 'three'
			? 'border-2 border-primary-500'
			: 'border-2 border-gray-300 border-dashed'}"
	>
		<p
			class="absolute -top-3 {activityBackground} font-bold {activeActivity === 'three'
				? 'text-primary-500'
				: 'text-gray-500'}"
		>
			{m.activityThree()}
		</p>
		<div class="flex flex-row space-x-2">
			<div class="w-full">
				<AutocompleteSelect
					multiple
					{form}
					optionsEndpoint="applied-controls"
					optionsDetailedUrlParameters={[['scope_folder_id', $formData.folder]]}
					optionsExtraFields={[['folder', 'str']]}
					field="applied_controls"
					label={m.appliedControls()}
				/>
			</div>
			<div class="flex items-end">
				<button
					class="btn input h-11 w-11"
					aria-label={m.addAppliedControl()}
					onclick={modalMeasureCreateForm}
					type="button"
					><i class="fa-solid fa-plus text-sm"></i>
				</button>
			</div>
		</div>

		<h4 class="h4 font-semibold self-start">{m.targetAssessment()}</h4>
		<div class="flex flex-row items-center space-x-4">
			<div class="flex flex-col space-y-4 w-fit items-center">
				<span class="flex flex-row items-center space-x-4">
					<RadioGroup
						{form}
						possibleOptions={[
							{ label: '0', value: 0 },
							{ label: '1', value: 1 },
							{ label: '2', value: 2 },
							{ label: '3', value: 3 },
							{ label: '4', value: 4 }
						]}
						label={m.dependency()}
						field="residual_dependency"
						labelKey="label"
						key="value"
						cacheLock={cacheLocks['residual_dependency']}
						bind:cachedValue={formDataCache['residual_dependency']}
					/>
					<i class="fa-solid fa-times"></i>
					<RadioGroup
						{form}
						possibleOptions={[
							{ label: '0', value: 0 },
							{ label: '1', value: 1 },
							{ label: '2', value: 2 },
							{ label: '3', value: 3 },
							{ label: '4', value: 4 }
						]}
						label={m.penetration()}
						field="residual_penetration"
						labelKey="label"
						key="value"
						cacheLock={cacheLocks['residual_penetration']}
						bind:cachedValue={formDataCache['residual_penetration']}
					/>
				</span>

				<hr class="border-t-2! border-surface-900! self-stretch" />

				<span class="flex flex-row items-center space-x-4">
					<RadioGroup
						{form}
						possibleOptions={[
							{ label: '1', value: 1 },
							{ label: '2', value: 2 },
							{ label: '3', value: 3 },
							{ label: '4', value: 4 }
						]}
						label={m.maturity()}
						field="residual_maturity"
						labelKey="label"
						key="value"
						cacheLock={cacheLocks['residual_maturity']}
						bind:cachedValue={formDataCache['residual_maturity']}
					/>
					<i class="fa-solid fa-times"></i>
					<RadioGroup
						{form}
						possibleOptions={[
							{ label: '1', value: 1 },
							{ label: '2', value: 2 },
							{ label: '3', value: 3 },
							{ label: '4', value: 4 }
						]}
						label={m.trust()}
						field="residual_trust"
						labelKey="label"
						key="value"
						cacheLock={cacheLocks['residual_trust']}
						bind:cachedValue={formDataCache['residual_trust']}
					/></span
				>
			</div>
			<i class="fa-solid fa-equals"></i>
			<div class="flex flex-col mb-5">
				<label for="residual_criticality" class="text-sm font-semibold">
					{m.criticality()}
				</label>
				<span class="chip text-base text-center px-4 py-1 rounded-base preset-filled">
					{residualCriticality}
				</span>
			</div>
		</div>
	</div>
{/if}
