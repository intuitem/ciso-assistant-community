<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';
	import { page } from '$app/state';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import UpdateModal from '$lib/components/Modals/UpdateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	import { Tabs } from '@skeletonlabs/skeleton-svelte';

	import { canPerformAction } from '$lib/utils/access-control';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let group = $state(Object.keys(data.relatedModels)[0]);

	// Mapping of model types to their context names for selection
	const contextMap: Record<string, string> = {
		'compliance-assessments': 'selectComplianceAssessments',
		'risk-assessments': 'selectRiskAssessments',
		'quantitative-risk-studies': 'selectCrqStudies',
		'ebios-rm': 'selectEbiosStudies',
		'entity-assessments': 'selectEntityAssessments',
		'findings-assessments': 'selectFindingsAssessments',
		evidences: 'selectDocuments',
		'security-exceptions': 'selectSecurityExceptions',
		policies: 'selectPolicies',
		'generic-collections': 'selectDependencies'
	};

	// Mapping of model types to their field names in the form
	const fieldMap: Record<string, string> = {
		'compliance-assessments': 'compliance_assessments',
		'risk-assessments': 'risk_assessments',
		'quantitative-risk-studies': 'crq_studies',
		'ebios-rm': 'ebios_studies',
		'entity-assessments': 'entity_assessments',
		'findings-assessments': 'findings_assessments',
		evidences: 'documents',
		'security-exceptions': 'security_exceptions',
		policies: 'policies',
		'generic-collections': 'dependencies'
	};

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
		modalStore.trigger(modal);
	}

	function modalUpdateForm(urlmodel: string): void {
		const fieldName = fieldMap[urlmodel];
		const contextName = contextMap[urlmodel];

		if (!fieldName || !contextName || !data.updateForms[fieldName]) {
			console.error('No update form found for', urlmodel);
			return;
		}

		let modalComponent: ModalComponent = {
			ref: UpdateModal,
			props: {
				form: data.updateForms[fieldName],
				model: data.model,
				object: data.object,
				context: contextName
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('select-' + urlmodel)
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
</script>

<DetailView {data} displayModelTable={false} />
{#if Object.keys(data.relatedModels).length > 0}
	<div class="card shadow-lg mt-8 bg-white w-full">
		<Tabs
			value={group}
			onValueChange={(e) => {
				group = e.value;
			}}
			listJustify="justify-center"
		>
			{#snippet list()}
				{#each Object.entries(data.relatedModels).sort( ([a], [b]) => a.localeCompare(b) ) as [urlmodel, model]}
					<Tabs.Control value={urlmodel}>
						{safeTranslate(model.info.localNamePlural)}
						{#if model.table.body.length > 0}
							<span class="badge preset-tonal-secondary">{model.table.body.length}</span>
						{/if}
					</Tabs.Control>
				{/each}
			{/snippet}
			{#snippet content()}
				{#each Object.entries(data.relatedModels) as [urlmodel, model]}
					<Tabs.Panel value={urlmodel}>
						<div class="flex flex-row justify-between px-4 py-2">
							<h4 class="font-semibold lowercase capitalize-first my-auto">
								{safeTranslate('associated-' + model.info.localNamePlural)}
							</h4>
						</div>
						{#if model.table}
							{@const field = data.model.reverseForeignKeyFields?.find(
								(item) => item.urlModel === urlmodel
							)}
							<ModelTable
								source={model.table}
								deleteForm={model.deleteForm}
								URLModel={urlmodel}
								canSelectObject={canEditObject}
								baseEndpoint="/{urlmodel}?genericcollection={page.params.id}"
								disableDelete={true}
							>
								{#snippet selectButton()}
									<div>
										<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
											<button
												class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
												data-testid="select-button"
												title={safeTranslate('select-' + urlmodel)}
												onclick={(_) => modalUpdateForm(urlmodel)}
												><i class="fa-solid fa-hand-pointer"></i>
											</button>
										</span>
									</div>
								{/snippet}
								{#snippet addButton()}
									<div>
										<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
											<button
												class="inline-block border-e p-3 btn-mini-primary w-12 focus:relative"
												data-testid="add-button"
												title={safeTranslate('add-' + model.info.localName)}
												onclick={(_) => modalCreateForm(model)}
												><i class="fa-solid fa-file-circle-plus"></i>
											</button>
										</span>
									</div>
								{/snippet}
							</ModelTable>
						{/if}
					</Tabs.Panel>
				{/each}
			{/snippet}
		</Tabs>
	</div>
{/if}
