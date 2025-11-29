<script lang="ts">
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import { type ModelMapEntry } from '$lib/utils/crud';
	import { getModelInfo } from '$lib/utils/crud.js';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { isURL } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales.js';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime.js';

	import { Tooltip } from '@skeletonlabs/skeleton-svelte';

	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import { getListViewFields } from '$lib/utils/table';
	import { canPerformAction } from '$lib/utils/access-control';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { fade } from 'svelte/transition';

	const modalStore: ModalStore = getModalStore();

	const defaultExcludes = [
		'id',
		'is_published',
		'localization_dict',
		'str',
		'path',
		'sync_mappings'
	];

	interface Props {
		data: any;
		mailing?: boolean;
		fields?: string[];
		exclude?: string[];
		displayModelTable?: boolean;
		dateFieldsToFormat?: string[];
		widgets?: import('svelte').Snippet;
		actions?: import('svelte').Snippet;
		disableCreate?: boolean;
		disableEdit?: boolean;
		disableDelete?: boolean;
	}

	let {
		data = $bindable(),
		mailing = false,
		fields = [],
		exclude = $bindable([]),
		displayModelTable = true,
		dateFieldsToFormat = [
			'created_at',
			'updated_at',
			'expiry_date',
			'accepted_at',
			'rejected_at',
			'revoked_at',
			'eta',
			'expiration_date',
			'validation_deadline',
			'timestamp',
			'reported_at',
			'due_date',
			'start_date'
		],
		widgets,
		actions,
		disableCreate = false,
		disableEdit = false,
		disableDelete = false
	}: Props = $props();

	exclude = [...exclude, ...defaultExcludes];

	const getRelatedModelIndex = (model: ModelMapEntry, relatedModel: Record<string, string>) => {
		if (!model.reverseForeignKeyFields) return -1;
		return model.reverseForeignKeyFields.findIndex((o) => o.urlModel === relatedModel.urlModel);
	};

	let filteredData = $derived(
		data.model?.detailViewFields
			? Object.fromEntries(
					Object.entries(data.data).filter(
						([key, _]) =>
							data.model.detailViewFields.filter((field) => field.field === key).length > 0
					)
				)
			: data.data
	);

	// Get ordered entries based on detailViewFields configuration
	let orderedEntries = $derived(() => {
		if (data.model?.detailViewFields) {
			// Return entries in the order specified by detailViewFields
			return data.model.detailViewFields
				.map((fieldConfig) => [fieldConfig.field, data.data[fieldConfig.field]])
				.filter(([, value]) => value !== undefined);
		} else {
			// Fall back to original order from data object
			return Object.entries(filteredData);
		}
	});

	// Helper to get field configuration including tooltip
	const getFieldConfig = (fieldName: string) => {
		return data.model?.detailViewFields?.find((field) => field.field === fieldName);
	};

	let hasWidgets = $derived(!!widgets);

	function handleKeydown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey) return;
		if (document.activeElement?.tagName !== 'BODY') return;

		if (event.key === 'e' && displayEditButton()) {
			event.preventDefault();
			goto(`${page.url.pathname}/edit?next=${page.url.pathname}`);
		}
	}

	onMount(() => {
		document.addEventListener('keydown', handleKeydown);

		return () => {
			document.removeEventListener('keydown', handleKeydown);
		};
	});

	function modalCreateForm(model: Record<string, any>): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: model.createForm,
				model: model,
				debug: false,
				additionalInitialData: model.initialData,
				formAction: `/${model.urlModel}?/create`
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add-' + model.info.localName)
		};
		modalStore.trigger(modal);
	}

	function modalConfirm(id: string, name: string, action: string): void {
		const urlModel = getModelInfo('risk-acceptances').urlModel;
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: { id: id, urlmodel: urlModel },
				id: id,
				debug: false,
				URLModel: urlModel,
				formAction: action
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.confirmModalTitle(),
			body: `${m.confirmModalMessage()}: ${name}?`
		};
		modalStore.trigger(modal);
	}

	function modalAppliedControlDuplicateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.duplicateForm,
				model: data.model,
				debug: false,
				duplicate: true,
				formAction: '?/duplicate'
			}
		};

		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.duplicateAppliedControl()
		};
		modalStore.trigger(modal);
	}

	function modalMailConfirm(id: string, name: string, action: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: { id: id, urlmodel: getModelInfo('compliance-assessments').urlModel },
				id: id,
				debug: false,
				URLModel: getModelInfo('compliance-assessments').urlModel,
				formAction: action,
				bodyComponent: List,
				bodyProps: {
					items: data.data.representatives,
					message: m.theFollowingRepresentativesWillReceiveTheQuestionnaireColon()
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.confirmModalTitle(),
			body: m.sureToSendQuestionnaire({ questionnaire: name })
		};
		modalStore.trigger(modal);
	}

	function getReverseForeignKeyEndpoint({
		parentModel,
		targetUrlModel,
		field,
		id,
		endpointUrl
	}: {
		parentModel: ModelMapEntry;
		targetUrlModel: string;
		field: string;
		id: string;
		endpointUrl?: string;
	}) {
		if (endpointUrl?.startsWith('./')) {
			return `/${parentModel.urlmodel}/${id}/${endpointUrl.slice(2)}`;
		}
		return `/${targetUrlModel}?${field}=${id}`;
	}

	const user = page.data.user;
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: data.model.name,
		domain:
			data.model.name === 'folder'
				? data.data.id
				: (data.data.folder?.id ?? data.data.folder ?? user.root_folder_id)
	});

	let displayEditButton = $derived(function () {
		return (
			(canEditObject &&
				!['Submitted', 'Accepted', 'Rejected', 'Revoked'].includes(data.data.state) &&
				!data.data.urn &&
				!data.data.builtin) ||
			data?.urlModel === 'terminologies' ||
			data?.urlModel === 'entities'
		);
	});

	function getSortedRelatedModels() {
		return Object.entries(data?.relatedModels ?? {}).sort((a: [string, any], b: [string, any]) => {
			return getRelatedModelIndex(data.model, a[1]) - getRelatedModelIndex(data.model, b[1]);
		});
	}

	let relatedModels = $derived(getSortedRelatedModels());
	let relatedModelsNames: Set<string> = $state(new Set());

	let group = $state(
		Object.keys(data?.relatedModels ?? {}).length > 0 ? getSortedRelatedModels()[0][0] : undefined
	);

	// Modèle actif pour la navigation latérale
	let activeEntry = $derived(
		relatedModels.length > 0
			? relatedModels.find(([urlmodel]) => urlmodel === group) ?? relatedModels[0]
			: undefined
	);

	let activeUrlmodel = $derived(activeEntry ? activeEntry[0] : undefined);
	let activeModel = $derived(activeEntry ? activeEntry[1] : undefined);

	let activeField = $derived(
		activeUrlmodel
			? data.model.reverseForeignKeyFields?.find((item) => item.urlModel === activeUrlmodel)
			: undefined
	);

	let activeFieldsToUse = $derived(() => {
		if (!activeUrlmodel || !activeField) return [];

		const listConfig = getListViewFields({
			key: activeUrlmodel,
			featureFlags: page.data?.featureflags
		});

		if (activeField.tableFields) {
			return activeField.tableFields;
		}
		return listConfig.body.filter((v) => v !== activeField.field);
	});

	$effect(() => {
		const newRelatedModelsNames = new Set(relatedModels.map((model) => model[0]));

		const setsAreDifferent =
			relatedModelsNames.size !== newRelatedModelsNames.size ||
			[...newRelatedModelsNames].some((name) => !relatedModelsNames.has(name));

		if (setsAreDifferent) {
			relatedModelsNames = newRelatedModelsNames;
			group = relatedModelsNames.size > 0 ? relatedModels[0][0] : undefined;
		}
	});

	function truncateString(str: string, maxLength: number = 50): string {
		return str.length > maxLength ? str.slice(0, maxLength) + '...' : str;
	}

	let openStateRA = $state(false);

	let expandedTable = $state(false);
	const MAX_ROWS = 10;

	// NEW: collapse / expand object details
	let detailsCollapsed = $state(false);
</script>

<div class="flex flex-col space-y-2">
	{#if data.urlModel === 'risk-acceptances' && data.data.state === 'Created'}
		<div class="flex flex-row items-center bg-yellow-100 rounded-container shadow-sm px-6 py-2">
			<div class="text-yelloW-900">
				{m.riskAcceptanceNotYetSubmittedMessage()}
			</div>
		</div>
	{:else if data.data.state === 'Submitted' && page.data.user.id === data.data.approver.id}
		<div
			class="flex flex-row space-x-4 items-center bg-yellow-100 rounded-container shadow-sm px-6 py-2 justify-between"
		>
			<div class="text-yellow-900">
				{m.riskAcceptanceValidatingReviewMessage()}
			</div>
			<div class="flex space-x-2">
				<button
					onclick={(_) => {
						modalConfirm(data.data.id, data.data.name, '?/accept');
					}}
					onkeydown={(_) => modalConfirm(data.data.id, data.data.name, '?/accept')}
					class="btn preset-filled-success-500"
				>
					<i class="fas fa-check mr-2"></i> {m.validate()}</button
				>
				<button
					onclick={(_) => {
						modalConfirm(data.data.id, data.data.name, '?/reject');
					}}
					onkeydown={(_) => modalConfirm(data.data.id, data.data.name, '?/reject')}
					class="btn preset-filled-error-500"
				>
					<i class="fas fa-xmark mr-2"></i> {m.reject()}</button
				>
			</div>
		</div>
	{:else if data.data.state === 'Accepted'}
		<div
			class="flex flex-row items-center space-x-4 bg-green-100 rounded-container shadow-lg px-6 py-2 mt-2 justify-between"
		>
			<div class="text-green-900">
				{m.riskAcceptanceValidatedMessage()}
			</div>
			{#if page.data.user.id === data.data.approver.id}
				<div class="ml-auto whitespace-nowrap">
					<button
						onclick={(_) => {
							modalConfirm(data.data.id, data.data.name, '?/revoke');
						}}
						onkeydown={(_) => modalConfirm(data.data.id, data.data.name, '?/revoke')}
						class="btn preset-filled-error-500"
					>
						<i class="fas fa-xmark mr-2"></i> {m.revoke()}</button
					>
				</div>
			{/if}
		</div>
	{/if}

<!-- Main content area with collapsible object details -->
<div class="card shadow-lg bg-white">
	<div class="px-4 pt-4 pb-4">
		<!-- Wrapper pour positionner l’icône sans ajouter une ligne -->
		<div class="relative">
			<!-- Bouton œil / œil barré, flottant en haut à droite -->
		<button
			type="button"
			class="absolute top-0 right-0 inline-flex items-center p-1 rounded-full"
			onclick={() => (detailsCollapsed = !detailsCollapsed)}
			aria-label="toggle-details"
		>
			<i
				class={`fa-solid ${
					detailsCollapsed ? 'fa-chevron-down' : 'fa-chevron-up'
				} text-lg`}
			></i>
		</button>

			{#if !detailsCollapsed}
				<!-- On laisse un peu de marge en haut pour que l’œil ne chevauche pas le contenu -->
				<div class="pt-2" in:fade={{ duration: 150 }} out:fade={{ duration: 100 }}>
					{#each data.data?.sync_mappings as syncMapping}
						<div class="mb-4 p-4 bg-secondary-50 border-l-4 border-secondary-400">
							<h3 class="font-semibold text-secondary-800 mb-2">
								{m.syncedWith({ integrationName: syncMapping.provider?.toUpperCase() ?? 'UNKNOWN' })}
							</h3>

							<dl class="grid grid-cols-1 gap-1 sm:grid-cols-2 text-secondary-700">
								<dt class="font-medium">{m.remoteId()}</dt>
								<dd>{syncMapping.remote_id}</dd>

								<dt class="font-medium">{m.lastSynced()}</dt>
								<dd>{new Date(syncMapping.last_synced_at).toLocaleString(getLocale())}</dd>

								<dt class="font-medium">{m.status()}</dt>
								<dd>{safeTranslate(syncMapping.sync_status)}</dd>
							</dl>
						</div>
					{/each}

					<div class={hasWidgets ? 'flex flex-row flex-wrap gap-4' : 'w-full'}>
						<!-- Left side - Details (conditional width) -->
						<div
							class="flow-root rounded-lg border border-gray-100 py-3 shadow-xs {hasWidgets
								? 'flex-1 min-w-[300px]'
								: 'w-full'}"
						>
							<dl class="-my-3 divide-y divide-gray-100 text-sm">
								{#each orderedEntries().filter(([key, _]) => (fields.length > 0 ? fields.includes(key) : true) && !exclude.includes(key)) as [key, value], index}
									<div
										class="grid grid-cols-1 gap-1 py-3 px-2 even:bg-surface-50 sm:grid-cols-5 sm:gap-4 {index >=
											MAX_ROWS && !expandedTable
											? 'hidden'
											: ''}"
									>
										<dt
											class="font-medium text-gray-900 flex items-center gap-2"
											data-testid="{key.replace('_', '-')}-field-title"
										>
											<span>{safeTranslate(key)}</span>
											{#if getFieldConfig(key)?.tooltip}
												{@const tooltipKey = getFieldConfig(key)?.tooltip}
												{@const tooltipText = m[tooltipKey] ? m[tooltipKey]() : tooltipKey}
												<Tooltip
													positioning={{ placement: 'right' }}
													contentBase="card bg-gray-800 text-white p-3 max-w-xs shadow-xl border border-gray-700"
													openDelay={200}
													closeDelay={100}
													arrow
													arrowBase="arrow bg-gray-800 border border-gray-700"
												>
													{#snippet trigger()}
														<i
															class="fas fa-info-circle text-sm text-blue-500 hover:text-blue-600 cursor-help"
														></i>
													{/snippet}
													{#snippet content()}
														<p class="text-sm">{tooltipText}</p>
													{/snippet}
												</Tooltip>
											{/if}
										</dt>
										<dd class="text-gray-700 sm:col-span-4">
											<ul>
												<li
													class="list-none whitespace-pre-line"
													data-testid={!(value instanceof Array)
														? key.replace('_', '-') + '-field-value'
														: null}
												>
													{#if value !== null && value !== undefined && value !== ''}
														{#if key === 'asset_class'}
															<!-- ... ton code existant ... -->
														{:else if key === 'library'}
															<!-- ... -->
														{:else if Array.isArray(value)}
															<!-- ... -->
														{:else}
															{(value.str || value.name) ?? value}
														{/if}
													{:else}
														--
													{/if}
												</li>
											</ul>
										</dd>
									</div>
								{/each}
							</dl>
						</div>

						<!-- Right side - Widgets area (only if widgets exist) -->
						{#if hasWidgets}
							<div class="flex-1 min-w-[300px] flex flex-col">
								<div class="h-full">
									{@render widgets?.()}
								</div>
							</div>
						{/if}
					</div>

					{#if orderedEntries().filter(([key, _]) => (fields.length > 0 ? fields.includes(key) : true && !exclude.includes(key))).length > MAX_ROWS}
						<button
							onclick={() => (expandedTable = !expandedTable)}
							class="m-5 text-blue-800"
							aria-expanded={expandedTable}
						>
							<i class="{expandedTable ? 'fas fa-chevron-up' : 'fas fa-chevron-down'} mr-3"></i>
						</button>
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<!-- Bottom row for action buttons (toujours visible) -->
	<div class="flex flex-row justify-end mt-4 gap-2 px-4 pb-4 border-t border-gray-100">
		{#if mailing}
			<!-- ... tes boutons existants ... -->
		{/if}
		{#if data.data.state === 'Submitted' && canEditObject}
			<!-- ... -->
		{/if}
		{#if displayEditButton()}
			<!-- ... -->
		{/if}
		{@render actions?.()}
	</div>
</div>

</div>

{#snippet RelatedModelContent()}
	{#key activeUrlmodel}
		<div in:fade={{ duration: 150 }}>
			{#if activeModel && activeUrlmodel && activeField}
				<div class="max-w-full rounded-xl border border-gray-100 shadow-sm p-4">
					<div class="flex flex-row justify-between items-center mb-3">
						<h4 class="font-semibold lowercase capitalize-first">
							{safeTranslate('associated-' + activeModel.info.localNamePlural)}
						</h4>
						{#if activeModel.table?.body?.length > 0}
							<span class="text-xs text-gray-500">
								{activeModel.table.body.length}
								&nbsp;{safeTranslate(activeModel.info.localNamePlural)}
							</span>
						{/if}
					</div>

					{#if activeModel.table}
						<ModelTable
							baseEndpoint={getReverseForeignKeyEndpoint({
								parentModel: data.model,
								targetUrlModel: activeUrlmodel,
								field: activeField.field,
								id: data.data.id,
								endpointUrl: activeField.endpointUrl
							})}
							source={activeModel.table}
							disableCreate={disableCreate || activeModel.disableCreate}
							disableEdit={disableEdit || activeModel.disableEdit}
							disableDelete={disableDelete || activeModel.disableDelete}
							deleteForm={activeModel.deleteForm}
							URLModel={activeUrlmodel}
							fields={activeFieldsToUse}
							defaultFilters={activeField.defaultFilters || {}}
						>
							{#snippet addButton()}
								<button
									class="btn preset-filled-primary-500 self-end my-auto"
									data-testid="add-button"
									onclick={(_) => modalCreateForm(activeModel)}
								>
									<i class="fa-solid fa-plus mr-2 lowercase"></i>
									{safeTranslate('add-' + activeModel.info.localName)}
								</button>
							{/snippet}
						</ModelTable>
					{:else}
						<p class="text-sm text-gray-500">
							{m.noDataAvailable()}
						</p>
					{/if}
				</div>
			{:else}
				<p class="text-sm text-gray-500">
					{m.noDataAvailable()}
				</p>
			{/if}
		</div>
	{/key}
{/snippet}

{#if relatedModels.length > 0 && displayModelTable}
	{#if relatedModels.length === 1}
		<!-- Single link: no side menu -->
		<div class="card shadow-lg mt-8 bg-white">
			<div class="px-4 py-4 overflow-x-auto">
				{@render RelatedModelContent()}
			</div>
		</div>
	{:else}
		<!-- General case with side menu -->
		<div class="card shadow-lg mt-8 bg-white">
			<div class="flex flex-col md:flex-row">
				<!-- sticky side bar -->
				<nav
					class="md:w-64 md:sticky md:top-[80px] md:h-[calc(100vh-120px)] md:overflow-y-auto
						bg-surface-50 border-b md:border-b-0 md:border-r border-gray-200
						pt-4"
				>
					<h3 class="px-4 pb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
						{safeTranslate('associated-objects')}
					</h3>

					<ul class="pb-4 space-y-1">
						{#each relatedModels as [urlmodel, model]}
							{@const isActive = group === urlmodel}
							<li>
								<button
									type="button"
									class={`
										w-full flex items-center justify-between px-4 py-2 text-left text-sm transition rounded-r-lg
										${isActive
											? 'bg-primary-50 text-primary-800 border-l-4 border-primary-500 font-semibold shadow-sm'
											: 'hover:bg-gray-50 text-gray-700 border-l-4 border-transparent'}
									`}
									onclick={() => (group = urlmodel)}
								>
									<div class="flex items-center gap-2">
										<span class="lowercase capitalize-first">
											{safeTranslate(model.info.localNamePlural)}
										</span>
									</div>
									{#if model.table?.body?.length > 0}
										<span class="badge preset-tonal-secondary">
											{model.table.body.length}
										</span>
									{/if}
								</button>
							</li>
						{/each}
					</ul>
				</nav>
				<!-- active section -->
				<div class="flex-1 px-4 py-4 overflow-x-auto">
					{@render RelatedModelContent()}
				</div>
			</div>
		</div>
	{/if}
{/if}
