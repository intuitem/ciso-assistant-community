<script lang="ts">
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import { m } from '$paraglide/messages';
	import TextArea from '../TextArea.svelte';
	import Checkbox from '../Checkbox.svelte';
	import RadioGroupInput from '../RadioGroupInput.svelte';
	import { getModalStore, type ModalComponent, type ModalSettings } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { page } from '$app/stores';
	import { safeTranslate } from '$lib/utils/i18n';

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

	const modalStore = getModalStore();

	function modalMeasureCreateForm(): void {
		const measureModel = $page.data.measureModel;
		console.log('measureModel', measureModel);
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: $page.data.measureCreateForm,
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

	const activityBackground = context === 'edit' ? 'bg-white' : 'bg-surface-100-800-token';
	const activeActivity: string = $page.url.searchParams.get('activity') || '';

	const getCriticality = (
		dependency: number,
		penetration: number,
		maturity: number,
		trust: number
	) => {
		if (maturity === 0 || trust === 0) return 0;
		return ((dependency * penetration) / (maturity * trust)).toFixed(2).replace(/\.?0+$/, '');
	};

	let currentCriticality = $derived(getCriticality(
		$formData.current_dependency,
		$formData.current_penetration,
		$formData.current_maturity,
		$formData.current_trust
	));

	let residualCriticality = $derived(getCriticality(
		$formData.residual_dependency,
		$formData.residual_penetration,
		$formData.residual_maturity,
		$formData.residual_trust
	));
</script>

<div
	class="relative p-2 space-y-2 rounded-container-token {activeActivity === 'one'
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
	<div class="flex flex-wrap items-center gap-4">
		<div>
			<span class="flex flex-row space-x-4">
				<Select
					{form}
					options={model.selectOptions['category']}
					field="category"
					label={m.category()}
					cacheLock={cacheLocks['category']}
					bind:cachedValue={formDataCache['category']}
					helpText={m.stakeholderCategoryHelpText()}
				/>
				<AutocompleteSelect
					{form}
					optionsEndpoint="entities"
					field="entity"
					cacheLock={cacheLocks['entity']}
					bind:cachedValue={formDataCache['entity']}
					label={m.entity()}
					hidden={initialData.entity}
					helpText={m.stakeholderEntityHelpText()}
				/>
			</span>

			<h4 class="h4 font-semibold self-start">{m.currentAssessment()}</h4>
			<div class="flex flex-row items-center space-x-4">
				<div class="flex flex-col space-y-4 w-fit items-center">
					<span class="flex flex-row items-center space-x-4">
						<RadioGroupInput
							{form}
							options={[
								{ label: '0', value: 0 },
								{ label: '1', value: 1 },
								{ label: '2', value: 2 },
								{ label: '3', value: 3 },
								{ label: '4', value: 4 }
							]}
							label={m.dependency()}
							field="current_dependency"
							cacheLock={cacheLocks['current_dependency']}
							bind:cachedValue={formDataCache['current_dependency']}
							helpText={m.dependencyHelpText()}
						/>
						<i class="fa-solid fa-times"></i>
						<RadioGroupInput
							{form}
							options={[
								{ label: '0', value: 0 },
								{ label: '1', value: 1 },
								{ label: '2', value: 2 },
								{ label: '3', value: 3 },
								{ label: '4', value: 4 }
							]}
							field="current_penetration"
							label={m.penetration()}
							cacheLock={cacheLocks['current_penetration']}
							bind:cachedValue={formDataCache['current_penetration']}
							helpText={m.penetrationHelpText()}
						/>
					</span>

					<hr class="!border-t-2 !border-surface-900 self-stretch" />

					<span class="flex flex-row items-center space-x-4">
						<RadioGroupInput
							{form}
							options={[
								{ label: '1', value: 1 },
								{ label: '2', value: 2 },
								{ label: '3', value: 3 },
								{ label: '4', value: 4 }
							]}
							field="current_maturity"
							label={m.maturity()}
							cacheLock={cacheLocks['current_maturity']}
							bind:cachedValue={formDataCache['current_maturity']}
							helpText={m.maturityHelpText()}
						/>
						<i class="fa-solid fa-times"></i>
						<RadioGroupInput
							{form}
							options={[
								{ label: '1', value: 1 },
								{ label: '2', value: 2 },
								{ label: '3', value: 3 },
								{ label: '4', value: 4 }
							]}
							field="current_trust"
							label={m.trust()}
							cacheLock={cacheLocks['current_trust']}
							bind:cachedValue={formDataCache['current_trust']}
							helpText={m.trustHelpText()}
						/></span
					>
				</div>
				<i class="fa-solid fa-equals"></i>
				<div class="flex flex-col mb-5">
					<label for="current_criticality" class="text-sm font-semibold">
						{m.criticality()}
					</label>
					<span class="chip text-base text-center px-4 py-1 rounded-token variant-filled">
						{currentCriticality}
					</span>
				</div>
			</div>
		</div>
		<div class="flex flex-col flex-grow">
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
	</div>
</div>

{#if context === 'edit'}
	<div
		class="relative p-2 space-y-2 rounded-container-token {activeActivity === 'three'
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
					optionsExtraFields={[['folder', 'str']]}
					field="applied_controls"
					label={m.appliedControls()}
				/>
			</div>
			<div class="flex items-end">
				<button class="btn input h-11 w-11" onclick={modalMeasureCreateForm} type="button"
					><i class="fa-solid fa-plus text-sm"></i>
				</button>
			</div>
		</div>

		<h4 class="h4 font-semibold self-start">{m.targetAssessment()}</h4>
		<div class="flex flex-row items-center space-x-4">
			<div class="flex flex-col space-y-4 w-fit items-center">
				<span class="flex flex-row items-center space-x-4">
					<RadioGroupInput
						{form}
						options={[
							{ label: '0', value: 0 },
							{ label: '1', value: 1 },
							{ label: '2', value: 2 },
							{ label: '3', value: 3 },
							{ label: '4', value: 4 }
						]}
						label={m.dependency()}
						field="residual_dependency"
						cacheLock={cacheLocks['residual_dependency']}
						bind:cachedValue={formDataCache['residual_dependency']}
					/>
					<i class="fa-solid fa-times"></i>
					<RadioGroupInput
						{form}
						options={[
							{ label: '0', value: 0 },
							{ label: '1', value: 1 },
							{ label: '2', value: 2 },
							{ label: '3', value: 3 },
							{ label: '4', value: 4 }
						]}
						field="residual_penetration"
						label={m.penetration()}
						cacheLock={cacheLocks['residual_penetration']}
						bind:cachedValue={formDataCache['residual_penetration']}
					/>
				</span>

				<hr class="!border-t-2 !border-surface-900 self-stretch" />

				<span class="flex flex-row items-center space-x-4">
					<RadioGroupInput
						{form}
						options={[
							{ label: '1', value: 1 },
							{ label: '2', value: 2 },
							{ label: '3', value: 3 },
							{ label: '4', value: 4 }
						]}
						field="residual_maturity"
						label={m.maturity()}
						cacheLock={cacheLocks['residual_maturity']}
						bind:cachedValue={formDataCache['residual_maturity']}
					/>
					<i class="fa-solid fa-times"></i>
					<RadioGroupInput
						{form}
						options={[
							{ label: '1', value: 1 },
							{ label: '2', value: 2 },
							{ label: '3', value: 3 },
							{ label: '4', value: 4 }
						]}
						field="residual_trust"
						label={m.trust()}
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
				<span class="chip text-base text-center px-4 py-1 rounded-token variant-filled">
					{residualCriticality}
				</span>
			</div>
		</div>
	</div>
{/if}
