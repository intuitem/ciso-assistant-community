<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { listViewFields } from '$lib/utils/table';
	import { m } from '$paraglide/messages';
	import { Tabs } from '@skeletonlabs/skeleton-svelte';
	import type { PageData } from './$types';
	import ValidationFlowCard from './ValidationFlowCard.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const userId = page.data.user.id;

	const tableSource = (() => {
		const fields = listViewFields['validation-flows'];
		return {
			head: fields.body.reduce((acc, key, index) => {
				acc[key] = fields.head[index];
				return acc;
			}, {}),
			body: [],
			filters: fields.filters
		};
	})();

	const emptyStates: Record<string, { icon: string; title: string; hint: string }> = {
		received: {
			icon: 'fa-clipboard-check',
			title: m.noPendingValidations(),
			hint: m.noPendingValidationsHint()
		},
		sent: {
			icon: 'fa-paper-plane',
			title: m.noSentValidations(),
			hint: m.noSentValidationsHint()
		},
		history: {
			icon: 'fa-clock-rotate-left',
			title: m.noValidationHistory(),
			hint: m.noValidationHistoryHint()
		}
	};

	function handleTabChange(tab: string): void {
		const url = new URL(page.url);
		url.searchParams.set('tab', tab);
		goto(url, { invalidateAll: true });
	}

	function modalCreateForm(): void {
		const modal: ModalSettings = {
			type: 'component',
			component: {
				ref: CreateModal,
				props: { form: data.createForm, model: data.model }
			},
			title: safeTranslate('add-' + data.model.localName)
		};
		modalStore.trigger(modal);
	}
</script>

<div class="relative">
	<button
		class="btn btn-sm preset-filled-primary-500 absolute right-0 top-0 z-10"
		data-testid="add-button"
		onclick={modalCreateForm}
	>
		<i class="fa-solid fa-file-circle-plus mr-2"></i>
		{safeTranslate('add-' + data.model.localName)}
	</button>

	<Tabs value={data.tab} onValueChange={(e) => handleTabChange(e.value)}>
		<Tabs.List>
			<Tabs.Trigger value="received" data-testid="tab-received">
				{m.validationsReceived()}
				{#if data.counts.received}
					<span class="badge preset-filled-primary-500 ml-2">{data.counts.received}</span>
				{/if}
			</Tabs.Trigger>
			<Tabs.Trigger value="sent" data-testid="tab-sent">
				{m.validationsSent()}
				{#if data.counts.sent}
					<span class="badge preset-tonal-surface ml-2">{data.counts.sent}</span>
				{/if}
			</Tabs.Trigger>
			<Tabs.Trigger value="history" data-testid="tab-history">
				{m.validationsHistory()}
				{#if data.counts.history}
					<span class="badge preset-tonal-surface ml-2">{data.counts.history}</span>
				{/if}
			</Tabs.Trigger>
			<Tabs.Trigger value="all" data-testid="tab-all">{m.all()}</Tabs.Trigger>
			<Tabs.Indicator />
		</Tabs.List>

		<div class="pt-4">
			{#if data.tab === 'all'}
				<Tabs.Content value="all">
					<div class="shadow-lg">
						<ModelTable
							source={tableSource}
							tableFilters={tableSource.filters}
							deleteForm={data.deleteForm}
							URLModel="validation-flows"
							disableEdit={true}
						/>
					</div>
				</Tabs.Content>
			{:else}
				<Tabs.Content value={data.tab}>
					{#if data.flows.length}
						<div class="flex flex-col gap-3">
							{#each data.flows as flow (flow.id)}
								<ValidationFlowCard
									{flow}
									{userId}
									counterpart={data.tab === 'sent' ? 'approver' : 'requester'}
								/>
							{/each}
						</div>
					{:else}
						<div
							class="flex flex-col items-center justify-center text-center py-16 gap-2"
							data-testid="validation-flows-empty-state"
						>
							<i
								class="fa-solid {emptyStates[data.tab]
									.icon} text-3xl text-surface-400-600 border border-surface-300-700 rounded-full p-5"
							></i>
							<p class="font-semibold mt-2">{emptyStates[data.tab].title}</p>
							<p class="text-sm text-surface-600-400 max-w-md">{emptyStates[data.tab].hint}</p>
						</div>
					{/if}
				</Tabs.Content>
			{/if}
		</div>
	</Tabs>
</div>
