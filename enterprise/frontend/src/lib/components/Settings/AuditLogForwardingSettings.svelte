<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import AuditSinkCreateModal from './AuditSinkCreateModal.svelte';
	import AuditSinkReplayModal from './AuditSinkReplayModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		data: any;
	}

	let { data }: Props = $props();

	function modalCreate(): void {
		const modalComponent: ModalComponent = {
			ref: AuditSinkCreateModal,
			props: {
				form: data.auditSinkCreateForm,
				formAction: '?/createAuditSink',
				invalidateAll: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.addAuditSink()
		};
		modalStore.trigger(modal);
	}

	function modalEdit(sink: Record<string, any>): void {
		const modalComponent: ModalComponent = {
			ref: AuditSinkCreateModal,
			props: {
				form: data.auditSinkCreateForm,
				formAction: '?/updateAuditSink',
				initialData: sink,
				invalidateAll: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.editAuditSink()
		};
		modalStore.trigger(modal);
	}

	function modalReplay(id: string): void {
		const modalComponent: ModalComponent = {
			ref: AuditSinkReplayModal,
			props: { id, formAction: '?/replayAuditSink', invalidateAll: true }
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.replayAuditEvents()
		};
		modalStore.trigger(modal);
	}
</script>

{#if page.data?.featureflags?.audit_log_forwarding}
	<div class="flex flex-col gap-6">
		<span class="text-gray-500">{m.configureAuditLogForwarding()}</span>

		<div class="flex items-center justify-between">
			<h3 class="text-base font-semibold flex items-center gap-2">
				<i class="fa-solid fa-shield-halved text-sm text-primary-500"></i>
				{m.auditSinks()}
			</h3>
			<button class="btn btn-sm preset-filled-primary-500" onclick={modalCreate}>
				<i class="fa-solid fa-plus mr-1"></i>
				{m.addAuditSink()}
			</button>
		</div>

		{#if data?.auditSinks?.length}
			<div class="flex flex-col gap-3">
				{#each data.auditSinks as sink (sink.id)}
					<div
						class="card bg-white shadow-sm border border-gray-200 p-4 flex items-center justify-between gap-4"
					>
						<div class="flex flex-col min-w-0">
							<div class="flex items-center gap-2">
								<span class="font-semibold truncate">{sink.name}</span>
								<span
									class="badge {sink.is_active ? 'preset-tonal-success' : 'preset-tonal-surface'}"
								>
									{sink.is_active ? m.active() : m.inactive()}
								</span>
								<span class="badge preset-tonal-primary uppercase">{sink.body_format}</span>
							</div>
							<span class="text-sm text-gray-500 truncate">
								{#if sink.transport === 'kafka'}
									{sink.kafka_config?.bootstrap_servers}
								{:else}
									{sink.url}
								{/if}
							</span>
						</div>
						<div class="flex items-center gap-2 shrink-0">
							<button class="btn btn-sm preset-tonal-surface" onclick={() => modalEdit(sink)}>
								<i class="fa-solid fa-pen-to-square mr-1"></i>
								{m.edit()}
							</button>
							<button
								class="btn btn-sm preset-tonal-secondary"
								onclick={() => modalReplay(sink.id)}
							>
								<i class="fa-solid fa-clock-rotate-left mr-1"></i>
								{m.replayAuditEvents()}
							</button>
							<form
								method="POST"
								action="?/deleteAuditSink"
								use:enhance
								onsubmit={(e) => {
									if (!confirm(m.deleteModalMessage({ name: sink.name }))) e.preventDefault();
								}}
							>
								<input type="hidden" name="id" value={sink.id} />
								<button class="btn btn-sm preset-tonal-error" type="submit" aria-label={m.delete()}>
									<i class="fa-solid fa-trash"></i>
								</button>
							</form>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<p class="text-sm text-gray-500 italic">{m.noAuditSinks()}</p>
		{/if}
	</div>
{:else}
	<span class="text-gray-500">{safeTranslate('auditLogForwardingDisabled')}</span>
{/if}
