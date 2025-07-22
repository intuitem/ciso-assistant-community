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

	import { Tabs, Tooltip } from '@skeletonlabs/skeleton-svelte';

	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { getListViewFields } from '$lib/utils/table';
	import { canPerformAction } from '$lib/utils/access-control';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	const defaultExcludes = ['id', 'is_published', 'localization_dict', 'str'];

	interface Props {
		data: any;
		mailing?: boolean;
		fields?: string[];
		exclude?: string[];
		displayModelTable?: boolean;
		dateFieldsToFormat?: string[];
		widgets?: import('svelte').Snippet;
		actions?: import('svelte').Snippet;
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
			'timestamp',
			'reported_at',
			'due_date',
			'start_date'
		],
		widgets,
		actions
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
			// Data
			title: m.confirmModalTitle(),
			body: m.sureToSendQuestionnaire({ questionnaire: name })
		};
		modalStore.trigger(modal);
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
			canEditObject &&
			!['Submitted', 'Accepted', 'Rejected', 'Revoked'].includes(data.data.state) &&
			!data.data.urn &&
			!data.data.builtin
		);
	});

	let relatedModels = $derived(
		Object.entries(data?.relatedModels ?? {}).sort((a: [string, any], b: [string, any]) => {
			return getRelatedModelIndex(data.model, a[1]) - getRelatedModelIndex(data.model, b[1]);
		})
	);

	let group = $derived(relatedModels.length > 0 ? relatedModels[0][0] : undefined);

	function truncateString(str: string, maxLength: number = 50): string {
		return str.length > maxLength ? str.slice(0, maxLength) + '...' : str;
	}

	let openStateRA = $state(false);
</script>

<div class="flex flex-col space-y-2">
	{#if data.data.state === 'Submitted' && page.data.user.id === data.data.approver.id}
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

	<!-- Main content area - modified to use flex layout -->
	<div class="card shadow-lg bg-white p-4">
		<div class="flex flex-row flex-wrap gap-4">
			<!-- Left side - Details (now takes half width) -->
			<div class="flow-root rounded-lg border border-gray-100 py-3 shadow-xs flex-1 min-w-[300px]">
				<dl class="-my-3 divide-y divide-gray-100 text-sm">
					{#each Object.entries(filteredData).filter( ([key, _]) => (fields.length > 0 ? fields.includes(key) : true && !exclude.includes(key)) ) as [key, value]}
						<div
							class="grid grid-cols-1 gap-1 py-3 px-2 even:bg-surface-50 sm:grid-cols-3 sm:gap-4"
						>
							<dt
								class="font-medium text-gray-900"
								data-testid="{key.replace('_', '-')}-field-title"
							>
								{safeTranslate(key)}
							</dt>
							<dd class="text-gray-700 sm:col-span-2">
								<ul class="">
									<li
										class="list-none whitespace-pre-line"
										data-testid={!(value instanceof Array)
											? key.replace('_', '-') + '-field-value'
											: null}
									>
										{#if value !== null && value !== undefined && value !== ''}
											{#if key === 'asset_class'}
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
											{:else if Array.isArray(value)}
												{#if Object.keys(value).length > 0}
													<ul>
														{#each value as val}
															<li data-testid={key.replace('_', '-') + '-field-value'}>
																{#if val.str && val.id}
																	{@const itemHref = `/${
																		data.model?.foreignKeyFields?.find((item) => item.field === key)
																			?.urlModel
																	}/${val.id}`}
																	<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
																		>{val.str}</Anchor
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
														>{value.str}</Anchor
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
											{:else if m[toCamelCase(value.str || value.name)]}
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

			<!-- Right side - New widgets and metrics area -->
			<div class="flex-1 min-w-[300px] flex flex-col">
				<!-- New slot for widgets and metrics -->
				<div class="h-full">
					{@render widgets?.()}
				</div>
			</div>
		</div>

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
				{#if data.data.state === 'Created'}
					<Tooltip
						open={openStateRA && !data.data.approver}
						onOpenChange={(e) => (openStateRA = e.open)}
						positioning={{ placement: 'top' }}
						contentBase="card preset-tonal-error p-4"
						openDelay={200}
						closeDelay={100}
						arrow
						arrowBase="arrow preset-tonal-surface border border-error-100"
						onclick={() => {
							if (data.data.approver) modalConfirm(data.data.id, data.data.name, '?/submit');
						}}
						onkeydown={(_: any) => {
							if (data.data.approver) return modalConfirm(data.data.id, data.data.name, '?/submit');
						}}
						triggerBase={data.data.approver
							? 'btn preset-filled-primary-500 *:pointer-events-none'
							: 'btn preset-filled-primary-500 opacity-50 *:pointer-events-none cursor-not-allowed'}
						disabled={data.data.approver}
					>
						{#snippet trigger()}
							<i class="fas fa-paper-plane mr-2"></i>
							{m.submit()}
						{/snippet}
						{#snippet content()}
							<p>{m.riskAcceptanceMissingApproverMessage()}</p>
						{/snippet}
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
	<div class="card shadow-lg mt-8 bg-white">
		<Tabs value={group} onValueChange={(e) => (group = e.value)} listJustify="justify-center">
			{#snippet list()}
				{#each relatedModels as [urlmodel, model]}
					<Tabs.Control value={urlmodel}>
						{safeTranslate(model.info.localNamePlural)}
						{#if model.table.body.length > 0}
							<span class="badge preset-tonal-secondary">{model.table.body.length}</span>
						{/if}
					</Tabs.Control>
				{/each}
			{/snippet}
			{#snippet content()}
				{#each relatedModels as [urlmodel, model]}
					<Tabs.Panel value={urlmodel}>
						{#key urlmodel}
							<div class="flex flex-row justify-between px-4 py-2">
								<h4 class="font-semibold lowercase capitalize-first my-auto">
									{safeTranslate('associated-' + model.info.localNamePlural)}
								</h4>
							</div>
							{@const field = data.model.reverseForeignKeyFields.find(
								(item) => item.urlModel === urlmodel
							)}
							{@const fieldsToUse = getListViewFields({
								key: urlmodel,
								featureFlags: page.data?.featureflags
							}).body.filter((v) => v !== field.field)}
							{#if model.table}
								<ModelTable
									baseEndpoint="/{model.urlModel}?{field.field}={data.data.id}"
									source={model.table}
									disableCreate={model.disableCreate}
									disableDelete={model.disableDelete}
									deleteForm={model.deleteForm}
									URLModel={urlmodel}
									fields={fieldsToUse}
								>
									{#snippet addButton()}
										<button
											class="btn preset-filled-primary-500 self-end my-auto"
											data-testid="add-button"
											onclick={(_) => modalCreateForm(model)}
											><i class="fa-solid fa-plus mr-2 lowercase"></i>{safeTranslate(
												'add-' + model.info.localName
											)}</button
										>
									{/snippet}
								</ModelTable>
							{/if}
						{/key}
					</Tabs.Panel>
				{/each}
			{/snippet}
		</Tabs>
	</div>
{/if}
