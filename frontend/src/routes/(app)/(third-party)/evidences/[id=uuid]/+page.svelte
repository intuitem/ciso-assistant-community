<script lang="ts">
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { getModelInfo } from '$lib/utils/crud.js';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton-svelte';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';
	import { defaults } from 'sveltekit-superforms';
	import { z } from 'zod';
	import { zod } from 'sveltekit-superforms/adapters';
	import { canPerformAction } from '$lib/utils/access-control';
	import { getModalStore } from '$lib/components/Modals/stores';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	interface Attachment {
		type: string;
		url: string;
		fileExists: boolean;
	}

	let attachment: Attachment | undefined = $state(undefined);
	const modalStore: ModalStore = getModalStore();

	function modalConfirm(id: string, name: string, action: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: defaults(
					{ id, urlmodel: 'evidences' },
					zod(z.object({ id: z.string(), urlmodel: z.string() }))
				),
				schema: zod(z.object({ id: z.string(), urlmodel: z.string() })),
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
			const res = await fetch(`./${data.data.id}/attachment`);
			const blob = await res.blob();
			return {
				type: blob.type,
				url: URL.createObjectURL(blob),
				fileExists: res.ok
			};
		};
		attachment = data.data.attachment ? await fetchAttachment() : undefined;
	});

	const user = page.data.user;
</script>

<DetailView {data} />

{#if data.data.attachment}
	<div class="card mt-8 px-6 py-4 bg-white flex flex-col shadow-lg space-y-4">
		<div class="flex flex-row justify-between">
			<h4 class="h4 font-semibold" data-testid="attachment-name-title">
				{data.data.attachment}
			</h4>
			<div class="space-x-2">
				<Anchor
					href={`./${data.data.id}/attachment`}
					class="btn preset-filled-primary-500 h-fit"
					data-testid="attachment-download-button"
					><i class="fa-solid fa-download mr-2"></i> {m.download()}</Anchor
				>
			</div>
		</div>
		{#if attachment}
			{#if attachment.type.startsWith('image')}
				<img src={attachment.url} alt="attachment" />
			{:else if attachment.type === 'application/pdf'}
				<embed src={attachment.url} type="application/pdf" width="100%" height="600px" />
			{:else}
				<div class="flex items-center justify-center space-x-4">
					{#if !attachment.fileExists}
						<p class="text-error-500 font-bold">{m.couldNotFindAttachmentMessage()}</p>
					{:else}
						<p class="font-bold text-sm">{m.NoPreviewMessage()}</p>
					{/if}
				</div>
			{/if}
		{:else}
			<span data-testid="loading-field">
				{m.loading()}...
			</span>
		{/if}
	</div>
{/if}
