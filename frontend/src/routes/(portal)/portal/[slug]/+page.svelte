<script lang="ts">
	import { goto } from '$app/navigation';
	import { safeTranslate } from '$lib/utils/i18n';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';
	import type { PageData } from './$types';

	interface PortalItem {
		icon: string;
		title: string;
		description?: string;
		kind: 'create' | 'navigate' | 'external' | 'status';
		target: { model?: string; url?: string };
	}

	let { data }: { data: PageData } = $props();
	const modalStore = getModalStore();

	function openCreate(model: string, title: string) {
		const entry = data.createForms[model];
		if (!entry) return;
		const component: ModalComponent = {
			ref: CreateModal,
			props: { form: entry.createForm, model: entry.model, formAction: `?/create&model=${model}` }
		};
		const modal: ModalSettings = { type: 'component', component, title };
		modalStore.trigger(modal);
	}

	function trigger(item: PortalItem) {
		if (item.kind === 'create' && item.target.model) openCreate(item.target.model, item.title);
		else if (item.kind === 'navigate' && item.target.url) goto(item.target.url);
		else if (item.kind === 'external' && item.target.url)
			window.open(item.target.url, '_blank', 'noopener');
	}
</script>

<div class="space-y-10">
	{#each data.portal?.sections ?? [] as section}
		<section>
			<h2 class="mb-4 text-sm font-semibold uppercase tracking-wide text-surface-500">
				{section.title}
			</h2>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each section.items as item}
					<button
						onclick={() => trigger(item)}
						class="group flex items-start gap-4 rounded-2xl border border-surface-200-800 bg-surface-50-950 p-5 text-left shadow-sm transition-all hover:border-violet-400 hover:shadow-md cursor-pointer"
					>
						<div
							class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-violet-500 to-fuchsia-500 text-white transition-transform group-hover:scale-110"
						>
							<i class="fa-solid {item.icon} text-lg"></i>
						</div>
						<div class="min-w-0">
							<div class="font-semibold text-surface-800-200">{safeTranslate(item.title)}</div>
							<div class="mt-0.5 text-xs text-surface-600-400">
								{safeTranslate(item.description)}
							</div>
						</div>
						{#if item.kind === 'external'}
							<i class="fa-solid fa-arrow-up-right-from-square ml-auto text-xs text-surface-400"
							></i>
						{/if}
					</button>
				{/each}
			</div>
		</section>
	{/each}
</div>
