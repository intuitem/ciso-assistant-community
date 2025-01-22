<script lang="ts">
	import { page } from '$app/stores';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import MissingConstraintsModal from '$lib/components/Modals/MissingConstraintsModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import { URL_MODEL_MAP, checkConstraints } from '$lib/utils/crud';
	import { getModelInfo } from '$lib/utils/crud.js';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { isURL } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales.js';
	import * as m from '$paraglide/messages.js';
	import { languageTag } from '$paraglide/runtime.js';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { Tab, TabGroup, getModalStore } from '@skeletonlabs/skeleton';

	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	const modalStore: ModalStore = getModalStore();

	const defaultExcludes = ['id', 'is_published', 'localization_dict'];

	export let data;
	export let mailing = false;
	export let fields: string[] = [];
	export let exclude: string[] = [];

	exclude = [...exclude, ...defaultExcludes];

	$: data.relatedModels = Object.fromEntries(Object.entries(data.relatedModels).sort());

	if (data.model.detailViewFields) {
		data.data = Object.fromEntries(
			Object.entries(data.data).filter(
				([key, _]) => data.model.detailViewFields.filter((field) => field.field === key).length > 0
			)
		);
	}

	let tabSet = 0;

	function handleKeydown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey) return;
		if (document.activeElement?.tagName !== 'BODY') return;
		// Check if the pressed key is 'e' and the edit button should be displayed

		if (event.key === 'e' && displayEditButton()) {
			event.preventDefault();
			goto(`${$page.url.pathname}/edit?next=${$page.url.pathname}`);
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
				debug: false
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + model.info.localName)
		};
		if (checkConstraints(model.createForm.constraints, model.foreignKeys).length > 0) {
			modalComponent = {
				ref: MissingConstraintsModal
			};
			modal = {
				type: 'component',
				component: modalComponent,
				title: m.warning(),
				body: safeTranslate('add-' + model.info.localName).toLowerCase(),
				value: checkConstraints(model.createForm.constraints, model.foreignKeys)
			};
		}
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

	const user = $page.data.user;
	const canEditObject: boolean = Object.hasOwn(user.permissions, `change_${data.model.name}`);

	$: displayEditButton = function () {
		return (
			canEditObject &&
			!['Accepted', 'Rejected', 'Revoked'].includes(data.data.state) &&
			!data.data.urn &&
			!data.data.builtin
		);
	};

	export let orderRelatedModels = [''];
	if (data.urlModel === 'projects') {
		orderRelatedModels = ['compliance-assessments', 'risk-assessments', 'entity-assessments'];
	}
	if (data.urlModel === 'entities') {
		orderRelatedModels = ['entity-assessments', 'representatives', 'solutions'];
	}
	if (data.urlModel === 'folders') {
		orderRelatedModels = ['projects', 'entities'];
	}
</script>

<div class="flex flex-col space-y-2">
	{#if data.data.state === m.submitted() && $page.data.user.id === data.data.approver.id}
		<div
			class="flex flex-row space-x-4 items-center bg-yellow-100 rounded-container-token shadow px-6 py-2 mb-2 justify-between"
		>
			<div class="text-yellow-900">
				{m.riskAcceptanceReviewMessage()}
			</div>
			<div class="flex space-x-2">
				<button
					on:click={(_) => {
						modalConfirm(data.data.id, data.data.name, '?/accept');
					}}
					on:keydown={(_) => modalConfirm(data.data.id, data.data.name, '?/accept')}
					class="btn variant-filled-success"
				>
					<i class="fas fa-check mr-2" /> {m.validate()}</button
				>
				<button
					on:click={(_) => {
						modalConfirm(data.data.id, data.data.name, '?/reject');
					}}
					on:keydown={(_) => modalConfirm(data.data.id, data.data.name, '?/reject')}
					class="btn variant-filled-error"
				>
					<i class="fas fa-xmark mr-2" /> {m.reject()}</button
				>
			</div>
		</div>
	{:else if data.data.state === m.accept()}
		<div
			class="flex flex-row items-center space-x-4 bg-green-100 rounded-container-token shadow-lg px-6 py-2 mt-2 justify-between"
		>
			<div class="text-green-900">
				{m.riskAcceptanceValidatedMessage()}
			</div>
			{#if $page.data.user.id === data.data.approver.id}
				<div class="ml-auto whitespace-nowrap">
					<button
						on:click={(_) => {
							modalConfirm(data.data.id, data.data.name, '?/revoke');
						}}
						on:keydown={(_) => modalConfirm(data.data.id, data.data.name, '?/revoke')}
						class="btn variant-filled-error"
					>
						<i class="fas fa-xmark mr-2" /> {m.revoke()}</button
					>
				</div>
			{/if}
		</div>
	{/if}
	<div class="card shadow-lg bg-white flex flex-row p-4 justify-between">
		<div class="flow-root rounded-lg border border-gray-100 py-3 shadow-sm w-3/4">
			<dl class="-my-3 divide-y divide-gray-100 text-sm">
				{#each Object.entries(data.data).filter( ([key, _]) => (fields.length > 0 ? fields.includes(key) : true && !exclude.includes(key)) ) as [key, value]}
					<div class="grid grid-cols-1 gap-1 py-3 px-2 even:bg-gray-50 sm:grid-cols-3 sm:gap-4">
						<dt class="font-medium text-gray-900" data-testid="{key.replace('_', '-')}-field-title">
							{safeTranslate(key)}
						</dt>
						<dd class="text-gray-700 sm:col-span-2">
							<ul class="">
								<li
									class="list-none"
									data-testid={!(value instanceof Array)
										? key.replace('_', '-') + '-field-value'
										: null}
								>
									{#if value !== null && value !== undefined && value !== ''}
										{#if key === 'library'}
											{@const itemHref = `/libraries/${value.id}?loaded`}
											<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
												>{value.name}</Anchor
											>
										{:else if key === 'severity'}
											<!-- We must add translations for the following severity levels -->
											<!-- Is this a correct way to convert the severity integer to the stringified security level ? -->
											{@const stringifiedSeverity =
												value < 0
													? '--'
													: (safeTranslate(['low', 'medium', 'high', 'critical'][value]) ??
														m.undefined())}
											{stringifiedSeverity}
										{:else if Array.isArray(value)}
											{#if Object.keys(value).length > 0}
												<ul>
													{#each value as val}
														<li data-testid={key.replace('_', '-') + '-field-value'}>
															{#if val.str && val.id}
																{@const itemHref = `/${
																	URL_MODEL_MAP[data.urlModel]['foreignKeyFields']?.find(
																		(item) => item.field === key
																	)?.urlModel
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
												URL_MODEL_MAP[data.urlModel]['foreignKeyFields']?.find(
													(item) => item.field === key
												)?.urlModel
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
										{:else if isURL(value) && !value.startsWith('urn')}
											<Anchor breadcrumbAction="push" href={value} target="_blank" class="anchor"
												>{value}</Anchor
											>
										{:else if ISO_8601_REGEX.test(value) && (key === 'created_at' || key === 'updated_at' || key === 'expiry_date' || key === 'accepted_at' || key === 'rejected_at' || key === 'revoked_at' || key === 'eta')}
											{formatDateOrDateTime(value, languageTag())}
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
		<div class="flex flex-col space-y-2 ml-4">
			{#if mailing}
				<button
					class="btn variant-filled-primary h-fit"
					on:click={(_) => {
						modalMailConfirm(
							data.data.compliance_assessment.id,
							data.data.compliance_assessment.str,
							'?/mailing'
						);
					}}
					on:keydown={(_) =>
						modalMailConfirm(
							data.data.compliance_assessment.id,
							data.data.compliance_assessment.str,
							'?/mailing'
						)}
				>
					<i class="fas fa-paper-plane mr-2" />
					{m.sendQuestionnaire()}
				</button>
			{/if}
			{#if displayEditButton()}
				<div class="flex flex-col space-y-2 ml-4">
					<Anchor
						breadcrumbAction="push"
						href={`${$page.url.pathname}/edit?next=${$page.url.pathname}`}
						label={m.edit()}
						class="btn variant-filled-primary h-fit"
						><i
							class="fa-solid fa-pen-to-square mr-2"
							data-testid="edit-button"
						/>{m.edit()}</Anchor
					>
					{#if data.urlModel === 'applied-controls'}
						<span class="pt-4 font-light text-sm">{m.powerUps()}</span>
						<button
							class="btn text-gray-100 bg-gradient-to-l from-sky-500 to-green-600"
							on:click={(_) => modalAppliedControlDuplicateForm()}
							data-testid="duplicate-button"
						>
							<i class="fa-solid fa-copy mr-2"></i>
							{m.duplicate()}</button
						>
					{/if}
				</div>
			{/if}
			<slot name="actions" />
		</div>
	</div>
</div>

{#if Object.keys(data.relatedModels).length > 0}
	<div class="card shadow-lg mt-8 bg-white">
		<TabGroup justify="justify-center">
			{#each Object.entries(data.relatedModels).sort((a, b) => {
				return orderRelatedModels.indexOf(a[0]) - orderRelatedModels.indexOf(b[0]);
			}) as [urlmodel, model], index}
				<Tab bind:group={tabSet} value={index} name={`${urlmodel}_tab`}>
					{safeTranslate(model.info.localNamePlural)}
					{#if model.table.body.length > 0}
						<span class="badge variant-soft-secondary">{model.table.body.length}</span>
					{/if}
				</Tab>
			{/each}
			<svelte:fragment slot="panel">
				{#each Object.entries(data.relatedModels).sort((a, b) => {
					return orderRelatedModels.indexOf(a[0]) - orderRelatedModels.indexOf(b[0]);
				}) as [urlmodel, model], index}
					{#if tabSet === index}
						<div class="flex flex-row justify-between px-4 py-2">
							<h4 class="font-semibold lowercase capitalize-first my-auto">
								{safeTranslate('associated-' + model.info.localNamePlural)}
							</h4>
						</div>
						{#if model.table}
							<ModelTable source={model.table} deleteForm={model.deleteForm} URLModel={urlmodel}>
								<button
									slot="addButton"
									class="btn variant-filled-primary self-end my-auto"
									on:click={(_) => modalCreateForm(model)}
									><i class="fa-solid fa-plus mr-2 lowercase" />{safeTranslate(
										'add-' + model.info.localName
									)}</button
								>
							</ModelTable>
						{/if}
					{/if}
				{/each}
			</svelte:fragment>
		</TabGroup>
	</div>
{/if}
