<script lang="ts">
	import type { PageData } from './$types';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { breadcrumbObject } from '$lib/utils/stores';
	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import type {
		ModalSettings,
		ModalComponent,
		ModalStore,
		ToastStore
	} from '@skeletonlabs/skeleton';
	import { getModalStore, TabGroup, Tab, getToastStore } from '@skeletonlabs/skeleton';
	import { isURL } from '$lib/utils/helpers';
	import { getModelInfo } from '$lib/utils/crud.js';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';

	import * as m from '$paraglide/messages';
	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let data: PageData;
	breadcrumbObject.set(data.evidence);

	interface Attachment {
		type: string;
		url: string;
	}

	let attachment: Attachment | undefined = undefined;

	const modalStore: ModalStore = getModalStore();
	const toastStore: ToastStore = getToastStore();

	function modalConfirm(id: string, name: string, action: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: data.evidence.form,
				id: id,
				debug: false,
				URLModel: getModelInfo('evidences').urlModel,
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

	onMount(async () => {
		const fetchAttachment = async () => {
			const res = await fetch(`./${data.evidence.id}/attachment`);
			const blob = await res.blob();
			return { type: blob.type, url: URL.createObjectURL(blob) };
		};
		attachment = data.evidence.attachment ? await fetchAttachment() : undefined;
	});

	const user = $page.data.user;
	const model = URL_MODEL_MAP['evidences'];
	const canEditObject: boolean = Object.hasOwn(user.permissions, `change_${model.name}`);

	let tabSet = 0;
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div class="card px-6 py-4 bg-white flex flex-row justify-between shadow-lg">
		<div class="flex flex-col space-y-2 whitespace-pre-line">
			{#each Object.entries(data.evidence).filter( ([key, _]) => ['name', 'description', 'folder', 'attachment', 'link', 'comment'].includes(key) ) as [key, value]}
				<div class="flex flex-col">
					<div
						class="text-sm font-medium text-gray-800 capitalize-first"
						data-testid={key.replace('_', '-') + '-field-title'}
					>
						{localItems()[toCamelCase(key)]}
					</div>
					<ul class="text-sm">
						<li
							class="text-gray-600 list-none"
							data-testid={!Array.isArray(value) || value.length <= 0
								? key.replace('_', '-') + '-field-value'
								: null}
						>
							{#if value}
								{#if Array.isArray(value)}
									<ul>
										{#if value.length > 0}
											{#each value as val}
												<li data-testid={key.replace('_', '-') + '-field-value'}>
													{#if val.str && val.id}
														{@const itemHref = `/${
															URL_MODEL_MAP[data.URLModel]['foreignKeyFields']?.find(
																(item) => item.field === key
															)?.urlModel
														}/${val.id}`}
														<a href={itemHref} class="anchor">{val.str}</a>
													{:else}
														{value}
													{/if}
												</li>
											{/each}
										{:else}
											--
										{/if}
									</ul>
								{:else if value.id}
									{@const itemHref = `/${
										URL_MODEL_MAP['evidences']['foreignKeyFields']?.find(
											(item) => item.field === key
										)?.urlModel
									}/${value.id}`}
									<a href={itemHref} class="anchor">{value.str}</a>
								{:else if isURL(value)}
									<a href={value} target="_blank" class="anchor">{value}</a>
								{:else}
									{value.str ?? value}
								{/if}
							{:else}
								--
							{/if}
						</li>
					</ul>
				</div>
			{/each}
		</div>
		<span>
			{#if canEditObject}
				<a
					href={`${$page.url.pathname}/edit?next=${$page.url.pathname}`}
					class="btn variant-filled-primary h-fit"
					data-testid="edit-button"><i class="fa-solid fa-pen-to-square mr-2" /> {m.edit()}</a
				>
			{/if}
		</span>
	</div>
	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg space-y-4">
		<TabGroup>
			<Tab bind:group={tabSet} name="compliance_assessments_tab" value={0}
				>{m.appliedControls()}</Tab
			>
			<Tab bind:group={tabSet} name="risk_assessments_tab" value={1}
				>{m.requirementAssessments()}</Tab
			>
			<svelte:fragment slot="panel">
				{#if tabSet === 0}
					<ModelTable source={data.tables['applied-controls']} URLModel="applied-controls" />
				{/if}
				{#if tabSet === 1}
					<ModelTable
						source={data.tables['requirement-assessments']}
						URLModel="requirement-assessments"
					/>
				{/if}
			</svelte:fragment>
		</TabGroup>
	</div>
	{#if data.evidence.attachment}
		<div class="card px-6 py-4 bg-white flex flex-col shadow-lg space-y-4">
			<div class="flex flex-row justify-between">
				<h4 class="h4 font-semibold" data-testid="attachment-name-title">
					{data.evidence.attachment}
				</h4>
				<div class="space-x-2">
					<a
						href={`./${data.evidence.id}/attachment`}
						class="btn variant-filled-primary h-fit"
						data-testid="attachment-download-button"
						><i class="fa-solid fa-download mr-2" /> {m.download()}</a
					>
					<button
						on:click={(_) => {
							modalConfirm(data.evidence.id, data.evidence.attachment, '?/deleteAttachment');
						}}
						on:keydown={(_) =>
							modalConfirm(data.evidence.id, data.evidence.attachment, '?/deleteAttachment')}
						class="btn variant-filled-tertiary h-full"><i class="fa-solid fa-trash" /></button
					>
				</div>
			</div>
			{#if attachment}
				{#if attachment.type.startsWith('image')}
					<img src={attachment.url} alt="attachment" />
				{:else if attachment.type === 'application/pdf'}
					<embed src={attachment.url} type="application/pdf" width="100%" height="600px" />
				{/if}
			{:else}
				<span data-testid="loading-field">
					{m.loading()}...
				</span>
			{/if}
		</div>
	{/if}
</div>
