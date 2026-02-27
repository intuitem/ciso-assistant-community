<script lang="ts">
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import SelectExistingModal from '$lib/components/Modals/SelectExistingModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import { type ModelMapEntry, type ReverseForeignKeyField } from '$lib/utils/crud';
	import { getModelInfo } from '$lib/utils/crud.js';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { isURL } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales.js';
	import { countMasked, isMaskedPlaceholder } from '$lib/utils/related-visibility';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime.js';

	import { Tabs, Tooltip } from '@skeletonlabs/skeleton-svelte';

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
				.filter(([key, value]) => value !== undefined);
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
	let relatedFieldNames = $derived(
		new Set(data.model?.foreignKeyFields?.map((field) => field.field) ?? [])
	);

	const getExpectedCount = (
		urlmodel: string,
		field?: ReverseForeignKeyField
	): number | undefined => {
		const candidates = [
			field?.expectedCountField,
			urlmodel ? urlmodel.replace(/-/g, '_') : undefined,
			field?.field
		].filter(Boolean) as string[];

		for (const candidate of candidates) {
			const value = data.data?.[candidate];
			if (Array.isArray(value)) {
				// Count how many {} (masked) objects are in the array
				return value.filter((item) => isMaskedPlaceholder(item)).length;
			}
		}
		return undefined;
	};

	function handleKeydown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey) return;
		if (document.activeElement?.tagName !== 'BODY') return;
		// Check if the pressed key is 'e' and the edit button should be displayed

		if (event.key === 'e' && displayEditButton()) {
			event.preventDefault();
			goto(`${page.url.pathname}/edit?next=${page.url.pathname}`);
		}
	}

	onMount(() => {
		// Add event listener to the document
		document.addEventListener('keydown', handleKeydown);

		// Cleanup function to remove event listener
		return () => {
			document.removeEventListener('keydown', handleKeydown);
		};
	});

	function modalCreateForm(model: Record<string, any>): void {
		let modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: model.createForm,
				model: model,
				debug: false,
				additionalInitialData: model.initialData,
				formAction: `/${model.urlModel}?/create`
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + model.info.localName)
		};
		modalStore.trigger(modal);
	}

	function modalSelectExisting(field: ReverseForeignKeyField): void {
		if (!field.addExisting || !data.updateForm) return;
		const addExisting = field.addExisting;
		const modalComponent: ModalComponent = {
			ref: SelectExistingModal,
			props: {
				form: data.updateForm,
				urlModel: data.urlModel,
				field: addExisting.parentField,
				optionsEndpoint: addExisting.optionsEndpoint ?? field.endpointUrl ?? field.urlModel,
				label: addExisting.label,
				optionsInfoFields: addExisting.optionsInfoFields
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate(addExisting.label ?? 'selectExisting')
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
			// Data
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

	function modalSendInvitation(id: string, email: string, action: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: { id: id, urlmodel: getModelInfo('representatives').urlModel, email: email },
				id: id,
				debug: false,
				URLModel: getModelInfo('representatives').urlModel,
				formAction: action
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.confirmModalTitle(),
			body: `Do you want to send the invitation to ${email}?`
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
			return `/${parentModel.urlModel}/${id}/${endpointUrl.slice(2)}`;
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
	$effect(() => {
		const newRelatedModelsNames = new Set(relatedModels.map((model) => model[0]));

		// Check if the sets are actually different
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

	// Check if there are non-visible objects and user can edit
	let hasNonVisibleObjects = $derived(() => {
		if (!canEditObject) return false;

		for (const [key, value] of Object.entries(data.data)) {
			if (Array.isArray(value)) {
				const maskedCount = countMasked(value);
				if (maskedCount > 0) return true;
			} else if (isMaskedPlaceholder(value)) {
				return true;
			}
		}
		return false;
	});
</script>

<div class="flex flex-col space-y-2">
	<!-- Warning for non-visible objects (only for users with edit permissions) -->

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

	<!-- Main content area - modified to use conditional flex layout -->
	<div class="card shadow-lg bg-white p-4">
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
						{@const isRelatedField = relatedFieldNames.has(key)}
						{@const hiddenCountForValue = isRelatedField ? countMasked(value) : 0}
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
									<Tooltip positioning={{ placement: 'right' }} openDelay={200} closeDelay={100}>
										<Tooltip.Trigger>
											<i
												class="fas fa-info-circle text-sm text-blue-500 hover:text-blue-600 cursor-help"
											></i>
										</Tooltip.Trigger>
										<Tooltip.Positioner>
											<Tooltip.Content
												class="card bg-gray-800 text-white p-3 max-w-xs shadow-xl border border-gray-700"
											>
												<p class="text-sm">{tooltipText}</p>
											</Tooltip.Content>
										</Tooltip.Positioner>
									</Tooltip>
								{/if}
							</dt>
							<dd class="text-gray-700 sm:col-span-4">
								<ul class="">
									<li
										class="list-none whitespace-pre-line"
										data-testid={!(value instanceof Array)
											? key.replace('_', '-') + '-field-value'
											: null}
									>
										{#if value !== null && value !== undefined && (value !== '' || hiddenCountForValue > 0)}
											{#if hiddenCountForValue > 0 && isMaskedPlaceholder(value) && !Array.isArray(value)}
												<p class="text-xs text-yellow-700">
													{m.objectsNotVisible({ count: hiddenCountForValue })}
												</p>
											{:else if key === 'asset_class'}
												<!-- Special case for asset_class - Always translate the value -->
												{#if typeof value === 'object' && (value.str || value.name)}
													{safeTranslate(value.str || value.name)}
												{:else}
													{safeTranslate(value)}
												{/if}
											{:else if key === 'library'}
												{@const itemHref = `/loaded-libraries/${value.id}`}
												<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
													>{value.name}</Anchor
												>
											{:else if key === 'severity' && data.urlModel !== 'incidents'}
												<!-- We must add translations for the following severity levels -->
												<!-- Is this a correct way to convert the severity integer to the stringified security level ? -->
												{@const stringifiedSeverity = !value
													? '--'
													: (safeTranslate(value) ?? m.undefined())}
												{stringifiedSeverity}
											{:else if key === 'children_assets'}
												{#if Object.keys(value).length > 0}
													<ul class="inline-flex flex-wrap space-x-4">
														{#each value as val}
															<li data-testid={key.replace('_', '-') + '-field-value'}>
																{#if val.str && val.id}
																	{@const itemHref = `/${
																		data.model?.foreignKeyFields?.find((item) => item.field === key)
																			?.urlModel
																	}/${val.id}`}
																	<Anchor breadcrumbAction="push" href={itemHref} class="anchor">
																		{truncateString(val.str)}</Anchor
																	>
																{:else if val.str}
																	{safeTranslate(val.str)}
																{:else}
																	{value}
																{/if}
															</li>
														{/each}
													</ul>
												{:else}
													--
												{/if}
											{:else if key === 'translations'}
												{#if Object.keys(value).length > 0}
													<div class="flex flex-col gap-2">
														{#each Object.entries(value) as [lang, translation]}
															<div class="flex flex-row gap-2">
																<strong>{lang}:</strong>
																<span>{safeTranslate(translation)}</span>
															</div>
														{/each}
													</div>
												{:else}
													--
												{/if}
											{:else if Array.isArray(value)}
												{@const visibleValues = isRelatedField
													? value.filter((item) => !isMaskedPlaceholder(item))
													: value}
												{#if visibleValues.length > 0}
													<ul>
														{#each [...visibleValues].sort((a, b) => {
															if ((!a.str && typeof a === 'object') || (!b.str && typeof b === 'object')) return 0;
															return safeTranslate(a.str || a).localeCompare(safeTranslate(b.str || b));
														}) as val}
															<li data-testid={key.replace('_', '-') + '-field-value'}>
																{#if key === 'purposes'}
																	{@const itemHref = `/${
																		data.model?.foreignKeyFields?.find((item) => item.field === key)
																			?.urlModel ?? 'purposes'
																	}/${val.id}`}
																	<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
																		>{val.name}</Anchor
																	>
																	{#if val.legal_basis}
																		<span class="text-gray-600">
																			- {safeTranslate(val.legal_basis)}
																		</span>
																	{/if}
																{:else if key === 'security_objectives' || key === 'security_capabilities'}
																	{@const [securityObjectiveName, securityObjectiveValue] =
																		Object.entries(val)[0]}
																	{safeTranslate(securityObjectiveName).toUpperCase()}: {securityObjectiveValue}
																{:else if val.str && val.id && key !== 'qualifications' && key !== 'relationship' && key !== 'nature'}
																	{@const itemHref = `/${
																		data.model?.foreignKeyFields?.find((item) => item.field === key)
																			?.urlModel
																	}/${val.id}`}
																	<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
																		>{safeTranslate(val.str)}</Anchor
																	>
																{:else if val.str}
																	{safeTranslate(val.str)}
																{:else}
																	{value}
																{/if}
															</li>
														{/each}
													</ul>
													{#if hiddenCountForValue > 0}
														<p class="mt-1 text-xs text-yellow-700">
															{m.objectsNotVisible({ count: hiddenCountForValue })}
														</p>
													{/if}
												{:else if hiddenCountForValue > 0}
													<p class="text-xs text-yellow-700">
														{m.objectsNotVisible({ count: hiddenCountForValue })}
													</p>
												{:else}
													--
												{/if}
											{:else if value.id && !value.hexcolor}
												{@const itemHref = `/${
													data.model?.foreignKeyFields?.find((item) => item.field === key)?.urlModel
												}/${value.id}`}
												{#if key === 'ro_to_couple'}
													<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
														>{safeTranslate(toCamelCase(value.str.split(' - ')[0]))} - {value.str.split(
															'-'
														)[1]}</Anchor
													>
												{:else}
													<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
														>{safeTranslate(value.str || value.name)}</Anchor
													>
												{/if}
												<!-- Shortcut before DetailView refactoring -->
											{:else if value === 'P1'}
												<li class="fa-solid fa-flag text-red-500"></li>
												{m.p1()}
											{:else if value === 'P2'}
												<li class="fa-solid fa-flag text-orange-500"></li>
												{m.p2()}
											{:else if value === 'P3'}
												<li class="fa-solid fa-flag text-blue-500"></li>
												{m.p3()}
											{:else if value === 'P4'}
												<li class="fa-solid fa-flag text-gray-500"></li>
												{m.p4()}
											{:else if key === 'icon'}
												<i class="text-lg fa {data.data.icon_fa_class}"></i>
												{safeTranslate((value.str || value.name) ?? value)}
											{:else if isURL(value) && !value.startsWith('urn')}
												<Anchor breadcrumbAction="push" href={value} target="_blank" class="anchor"
													>{value}</Anchor
												>
											{:else if ISO_8601_REGEX.test(value) && dateFieldsToFormat.includes(key)}
												{formatDateOrDateTime(value, getLocale())}
											{:else if key === 'description' || key === 'observation' || key === 'annotation'}
												<MarkdownRenderer content={value} />
											{:else if !['name', 'ref_id'].includes(key) && m[toCamelCase(value.str || value.name)]}
												{safeTranslate((value.str || value.name) ?? value)}
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
					<!-- Slot for widgets and metrics -->
					<div class="h-full">
						{@render widgets?.()}
					</div>
				</div>
			{/if}
		</div>
		{#if orderedEntries().filter( ([key, _]) => (fields.length > 0 ? fields.includes(key) : true && !exclude.includes(key)) ).length > MAX_ROWS}
			<button
				onclick={() => (expandedTable = !expandedTable)}
				class="m-5 text-blue-800"
				aria-expanded={expandedTable}
			>
				<i class="{expandedTable ? 'fas fa-chevron-up' : 'fas fa-chevron-down'} mr-3"></i>
				{expandedTable ? m.viewLess() : m.viewMore()}
			</button>
		{/if}

		<!-- Bottom row for action buttons -->
		<div class="flex flex-row justify-end mt-4 gap-2">
			{#if mailing}
				<button
					class="btn preset-filled-primary-500 h-fit"
					onclick={(_) => {
						modalMailConfirm(
							data.data.compliance_assessment.id,
							data.data.compliance_assessment.str,
							'?/mailing'
						);
					}}
					onkeydown={(_) =>
						modalMailConfirm(
							data.data.compliance_assessment.id,
							data.data.compliance_assessment.str,
							'?/mailing'
						)}
				>
					<i class="fas fa-paper-plane mr-2"></i>
					{m.sendQuestionnaire()}
				</button>
			{/if}

			{#if data.data.state === 'Submitted' && canEditObject}
				<button
					onclick={(_) => {
						modalConfirm(data.data.id, data.data.name, '?/draft');
					}}
					onkeydown={(_) => modalConfirm(data.data.id, data.data.name, '?/draft')}
					class="btn preset-filled-primary-500"
					disabled={!data.data.approver}
				>
					<i class="fas fa-arrow-alt-circle-left mr-2"></i> {m.draft()}</button
				>
			{/if}

			{#if displayEditButton()}
				{#if data.urlModel === 'representatives' && data.data.user}
					<button
						class="btn preset-filled-ghost-500 mr-2"
						onclick={() =>
							modalSendInvitation(
								data.data.id,
								data.data.email,
								`/representatives/${data.data.id}/send-invitation`
							)}
						data-testid="send-invitation-button"
					>
						<i class="fa-solid fa-envelope mr-2"></i>
						Send invitation
					</button>
				{/if}
				{#if data.data.state === 'Created'}
					<Tooltip
						open={openStateRA && !data.data.approver}
						onOpenChange={(e) => (openStateRA = e.open)}
						positioning={{ placement: 'top' }}
						openDelay={200}
						closeDelay={100}
					>
						<Tooltip.Trigger
							onclick={() => {
								if (data.data.approver) modalConfirm(data.data.id, data.data.name, '?/submit');
							}}
							onkeydown={(_: any) => {
								if (data.data.approver)
									return modalConfirm(data.data.id, data.data.name, '?/submit');
							}}
							class={data.data.approver
								? 'btn preset-filled-primary-500 *:pointer-events-none'
								: 'btn preset-filled-primary-500 opacity-50 *:pointer-events-none cursor-not-allowed'}
						>
							<i class="fas fa-paper-plane mr-2"></i>
							{m.submit()}
						</Tooltip.Trigger>
						{#if !data.data.approver}
							<Tooltip.Positioner>
								<Tooltip.Content class="card preset-tonal-error p-4">
									<p>{m.riskAcceptanceMissingApproverMessage()}</p>
								</Tooltip.Content>
							</Tooltip.Positioner>
						{/if}
					</Tooltip>
				{/if}

				<Anchor
					breadcrumbAction="push"
					href={`${page.url.pathname}/edit?next=${page.url.pathname}`}
					label={m.edit()}
					class="btn preset-filled-primary-500 h-fit"
					><i class="fa-solid fa-pen-to-square mr-2" data-testid="edit-button"
					></i>{m.edit()}</Anchor
				>

				{#if data.urlModel === 'applied-controls'}
					<button
						class="btn text-gray-100 bg-linear-to-l from-sky-500 to-green-600"
						onclick={(_) => modalAppliedControlDuplicateForm()}
						data-testid="duplicate-button"
					>
						<i class="fa-solid fa-copy mr-2"></i>
						{m.duplicate()}</button
					>
				{/if}
			{/if}
			{@render actions?.()}
		</div>
	</div>
</div>

{#if relatedModels.length > 0 && displayModelTable}
	<div class="card shadow-lg mt-8 bg-white py-6">
		<Tabs
			value={group}
			onValueChange={(e) => (group = e.value)}
			orientation="vertical"
			class="w-full"
		>
			<Tabs.List class="shrink-0 gap-3">
				{#each relatedModels as [urlmodel, model]}
					<Tabs.Trigger value={urlmodel} class="justify-start" data-testid="tabs-control">
						{safeTranslate(model.info.localNamePlural)}
						{#if model.count !== undefined && model.count > 0}
							<span class="badge preset-tonal-secondary">{model.count}</span>
						{/if}
					</Tabs.Trigger>
				{/each}
				<Tabs.Indicator />
			</Tabs.List>
			{#each relatedModels as [urlmodel, model]}
				<Tabs.Content value={urlmodel} class="flex-1 min-w-0">
					{#key urlmodel}
						<div class="py-2"></div>
						{@const field = data.model.reverseForeignKeyFields.find(
							(item) => item.urlModel === urlmodel
						)}
						{@const fieldsToUse =
							field?.tableFields ||
							getListViewFields({
								key: urlmodel,
								featureFlags: page.data?.featureflags
							}).body.filter((v) => v !== field.field)}
						{#if model.table}
							<ModelTable
								baseEndpoint={getReverseForeignKeyEndpoint({
									parentModel: data.model,
									targetUrlModel: urlmodel,
									field: field.field,
									id: data.data.id,
									endpointUrl: field.endpointUrl
								})}
								source={model.table}
								disableCreate={disableCreate || model.disableCreate}
								disableEdit={disableEdit || model.disableEdit}
								disableDelete={disableDelete || model.disableDelete}
								deleteForm={model.deleteForm}
								URLModel={urlmodel}
								expectedCount={getExpectedCount(urlmodel, field)}
								fields={fieldsToUse}
								defaultFilters={field.defaultFilters || {}}
							>
								{#snippet addButton()}
									{#if canEditObject && field?.addExisting}
										<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
											<button
												class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
												data-testid="select-existing-button"
												title={safeTranslate(field.addExisting.label ?? 'selectExisting')}
												onclick={() => modalSelectExisting(field)}
											>
												<i class="fa-solid fa-hand-pointer"></i>
											</button>
										</span>
										<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
											<button
												class="inline-block border-e p-3 btn-mini-primary w-12 focus:relative"
												data-testid="add-button"
												title={safeTranslate('add-' + model.info.localName)}
												onclick={(_) => modalCreateForm(model)}
											>
												<i class="fa-solid fa-file-circle-plus"></i>
											</button>
										</span>
									{:else}
										<button
											class="btn preset-filled-primary-500 self-end my-auto"
											data-testid="add-button"
											onclick={(_) => modalCreateForm(model)}
											><i class="fa-solid fa-plus mr-2 lowercase"></i>{safeTranslate(
												'add-' + model.info.localName
											)}</button
										>
									{/if}
								{/snippet}
							</ModelTable>
						{/if}
					{/key}
				</Tabs.Content>
			{/each}
		</Tabs>
	</div>
{/if}
