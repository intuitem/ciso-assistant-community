<script lang="ts">
	import type { PageData } from './$types';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { page } from '$app/stores';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import UpdateModal from '$lib/components/Modals/UpdateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { TabGroup, Tab, getModalStore } from '@skeletonlabs/skeleton';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { canPerformAction } from '$lib/utils/access-control';

	const modalStore: ModalStore = getModalStore();

	const statusMap = {
		planned: 'bg-indigo-300 text-indigo-800',
		in_progress: 'bg-yellow-300 text-yellow-800',
		in_review: 'bg-cyan-300 text-cyan-800',
		done: 'bg-lime-300 text-lime-800',
		deprecated: 'bg-orange-300 text-orange-800'
	};

	export let data: PageData;

	const ebiosRmStudy = data.data;

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

	let activeActivity: string | null = null;

	$page.url.searchParams.forEach((value, key) => {
		if (key === 'activity' && value === 'one') {
			activeActivity = 'one';
		} else if (key === 'activity' && value === 'two') {
			activeActivity = 'two';
		}
	});

	function modalUpdateForm(): void {
		let modalComponent: ModalComponent = {
			ref: UpdateModal,
			props: {
				form: data.updateForm,
				model: data.updatedModel,
				object: data.object,
				context: 'selectAsset'
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.selectAsset()
		};
		modalStore.trigger(modal);
	}

	let tabSet = 0;

	const user = $page.data.user;
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

<div class="card p-4 bg-white shadow-lg">
	<div class="flex flex-col space-y-4">
		<div class="flex flex-row justify-between items-center w-full">
			<a
				href="/ebios-rm/{ebiosRmStudy.id}"
				class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
			>
				<i class="fa-solid fa-arrow-left" />
				<p class="">{m.goBackToEbiosRmStudy()}</p>
			</a>
			<div class="flex items-center space-x-2">
				{#if ebiosRmStudy.ref_id}
					<span class="badge bg-pink-200 text-pink-800 font-medium">
						{m.refIdSemiColon()}
						{ebiosRmStudy.ref_id}
					</span>
				{/if}
				<span class="text-2xl font-bold">
					{ebiosRmStudy.name} - v{ebiosRmStudy.version}
				</span>
				<span class="badge text-xs {statusMap[ebiosRmStudy.status]}">
					{safeTranslate(ebiosRmStudy.status)}
				</span>
			</div>
			{#if canEditObject}
				<Anchor
					href={`${$page.url.pathname}/edit?activity=${activeActivity}&next=${$page.url.pathname}?activity=${activeActivity}`}
					class="btn variant-filled-primary h-fit"
				>
					<i class="fa-solid fa-pen-to-square mr-2" data-testid="edit-button" />
					{m.edit()}
				</Anchor>
			{/if}
		</div>
		<div class="flex justify-center items-center w-full gap-5">
			<span class="text-sm text-gray-500"
				>{m.referenceEntitySemiColon()}
				<a class="anchor" href="/entities/{ebiosRmStudy.reference_entity.id}"
					>{ebiosRmStudy.reference_entity.str}</a
				>
			</span>
			<span class="text-sm text-gray-500"
				>{m.ebiosRmMatrixHelpText()}
				<a class="anchor" href="/risk-matrices/{ebiosRmStudy.risk_matrix.id}"
					>{ebiosRmStudy.risk_matrix.str}</a
				>
			</span>
		</div>
		<div
			id="activityOne"
			class="relative p-4 space-y-4 rounded-md w-full flex flex-col items-center
                {activeActivity === 'one'
				? 'border-2 border-primary-500'
				: 'border-2 border-gray-300 border-dashed'}"
		>
			<span
				class="absolute -top-3 bg-white font-bold {activeActivity === 'one'
					? 'text-primary-500'
					: 'text-gray-500'}">{m.activityOne()}</span
			>
			{#if ebiosRmStudy.description}
				<p class="text-gray-600 whitespace-pre-wrap text-justify w-full">
					{ebiosRmStudy.description}
				</p>
			{:else}
				<p class="text-gray-600">{m.noDescription()}</p>
			{/if}
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-user text-purple-500"></i>
					<span>{m.authors()}</span>
				</h3>
				<ul class="list-disc list-inside text-gray-600">
					{#if ebiosRmStudy.authors?.length}
						{#each ebiosRmStudy.authors as author}
							<li><Anchor class="anchor" href="/users/{author.id}">{author.str}</Anchor></li>
						{/each}
					{:else}
						<li>{m.noAuthor()}</li>
					{/if}
				</ul>
			</div>
			<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
				<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
					<i class="fa-solid fa-users text-blue-500"></i>
					<span>{m.reviewers()}</span>
				</h3>
				<ul class="list-disc list-inside text-gray-600">
					{#if ebiosRmStudy.reviewers?.length}
						{#each ebiosRmStudy.reviewers as reviewer}
							<li><Anchor class="anchor" href="/users/{reviewer.id}">{reviewer.str}</Anchor></li>
						{/each}
					{:else}
						<li>{m.noReviewer()}</li>
					{/if}
				</ul>
			</div>
		</div>
		<div
			id="activityTwo"
			class="relative p-4 space-y-4 rounded-md w-full flex flex-col items-center
                {activeActivity === 'two'
				? 'border-2 border-primary-500'
				: 'border-2 border-gray-300 border-dashed'}"
		>
			<span
				class="absolute -top-3 bg-white font-bold {activeActivity === 'two'
					? 'text-primary-500'
					: 'text-gray-500'}">{m.activityTwo()}</span
			>
			{#if Object.keys(data.relatedModels).length > 0}
				<div class="card shadow-lg mt-8 bg-white w-full">
					<TabGroup justify="justify-center">
						{#each Object.entries(data.relatedModels) as [urlmodel, model], index}
							<Tab bind:group={tabSet} value={index} name={`${urlmodel}_tab`}>
								{safeTranslate(model.info.localNamePlural)}
								{#if model.table.body.length > 0}
									<span class="badge variant-soft-secondary">{model.table.body.length}</span>
								{/if}
							</Tab>
						{/each}
						<svelte:fragment slot="panel">
							{#each Object.entries(data.relatedModels) as [urlmodel, model], index}
								{#if tabSet === index}
									<div class="flex flex-row justify-between px-4 py-2">
										<h4 class="font-semibold lowercase capitalize-first my-auto">
											{safeTranslate('associated-' + model.info.localNamePlural)}
										</h4>
									</div>
									{#if model.table}
										<ModelTable
											source={model.table}
											deleteForm={model.deleteForm}
											URLModel={urlmodel}
											canSelectObject={canEditObject}
											baseEndpoint="/assets?ebios_rm_studies={$page.params.id}"
										>
											<div slot="selectButton">
												<span
													class="inline-flex overflow-hidden rounded-md border bg-white shadow-sm"
												>
													<button
														class="inline-block border-e p-3 btn-mini-secondary w-12 focus:relative"
														data-testid="select-button"
														title={m.selectAsset()}
														on:click={(_) => modalUpdateForm()}
														><i class="fa-solid fa-hand-pointer"></i>
													</button>
												</span>
											</div>
											<div slot="addButton">
												<span
													class="inline-flex overflow-hidden rounded-md border bg-white shadow-sm"
												>
													<button
														class="inline-block border-e p-3 btn-mini-primary w-12 focus:relative"
														data-testid="add-button"
														title={safeTranslate('add-' + data.model.localName)}
														on:click={(_) => modalCreateForm(model)}
														><i class="fa-solid fa-file-circle-plus"></i>
													</button>
												</span>
											</div>
										</ModelTable>
									{/if}
								{/if}
							{/each}
						</svelte:fragment>
					</TabGroup>
				</div>
			{/if}
		</div>
		<div class="w-full p-4 bg-gray-50 border rounded-md shadow-sm">
			<h3 class="font-semibold text-lg text-gray-700 flex items-center space-x-2">
				<i class="fa-solid fa-eye text-gray-500 opacity-75"></i>
				<span>{m.observation()}</span>
			</h3>
			{#if ebiosRmStudy.observation}
				<p class="text-gray-600">{ebiosRmStudy.observation}</p>
			{:else}
				<p class="text-gray-600">{m.noObservation()}</p>
			{/if}
		</div>
	</div>
</div>
