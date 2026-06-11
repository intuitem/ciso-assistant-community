<script lang="ts">
	import { m } from '$paraglide/messages';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import IdPGroupMappingCreateModal from '../../../routes/(app)/(internal)/settings/idp-group-mappings/IdPGroupMappingCreateModal.svelte';
	import { defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';

	const modalStore: ModalStore = getModalStore();

	interface Props {
		data: any;
	}

	let { data }: Props = $props();

	// Group synchronization policy
	let cfg = $state({
		enabled: data.groupSyncConfig?.enabled ?? false,
		authoritative: data.groupSyncConfig?.authoritative ?? false,
		oidc_groups_claim: data.groupSyncConfig?.oidc_groups_claim ?? 'groups',
		saml_groups_attribute: data.groupSyncConfig?.saml_groups_attribute ?? 'groups'
	});
	let savingCfg = $state(false);

	const ssoEnabled = $derived(data.ssoSettings?.is_enabled ?? false);

	function modalCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: IdPGroupMappingCreateModal,
			props: {
				form: data.idpGroupMappingCreateForm,
				formAction: '?/createIdpGroupMapping',
				invalidateAll: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.createIdpGroupMapping()
		};
		modalStore.trigger(modal);
	}

	function modalConfirmDelete(
		id: string,
		row: { [key: string]: string | number | boolean | null }
	): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: defaults({ id }, zod(z.object({ id: z.string() }))),
				id,
				debug: false,
				URLModel: 'idp-group-mappings',
				formAction: '?/deleteIdpGroupMapping'
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.deleteModalTitle(),
			body: m.deleteModalMessage({ name: String(row.external_group_id ?? '') })
		};
		modalStore.trigger(modal);
	}
</script>

<div class="flex flex-col gap-6">
	<span class="text-gray-500">{m.idpGroupMappingsDescription()}</span>

	{#if !ssoEnabled}
		<aside class="card bg-warning-50 border border-warning-300 p-3 flex items-start gap-3">
			<i class="fa-solid fa-triangle-exclamation text-warning-600 mt-0.5"></i>
			<div class="text-sm text-warning-800">
				{m.ssoNotEnabledWarning()}
				<a class="anchor font-medium" href="/settings?tab=sso">{m.sso()}</a>
			</div>
		</aside>
	{/if}

	<!-- Group synchronization policy -->
	<form
		method="POST"
		action="?/groupSync"
		use:enhance={() => {
			savingCfg = true;
			return async ({ update }) => {
				await update({ reset: false });
				await invalidateAll();
				savingCfg = false;
			};
		}}
		class="card bg-white shadow p-4 flex flex-col gap-4"
	>
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-rotate text-sm text-primary-500"></i>
			{m.groupSynchronization()}
		</h3>

		<input type="hidden" name="enabled" value={String(cfg.enabled)} />
		<input type="hidden" name="authoritative" value={String(cfg.authoritative)} />

		<label class="flex items-start gap-3 cursor-pointer">
			<input type="checkbox" class="checkbox mt-1" bind:checked={cfg.enabled} />
			<span class="flex flex-col">
				<span class="font-medium text-sm">{m.enableGroupSync()}</span>
				<span class="text-xs text-gray-500">{m.enableGroupSyncDescription()}</span>
			</span>
		</label>

		<label
			class="flex items-start gap-3 {cfg.enabled
				? 'cursor-pointer'
				: 'opacity-50 cursor-not-allowed'}"
		>
			<input
				type="checkbox"
				class="checkbox mt-1"
				bind:checked={cfg.authoritative}
				disabled={!cfg.enabled}
			/>
			<span class="flex flex-col">
				<span class="font-medium text-sm">{m.idpAuthoritative()}</span>
				<span class="text-xs text-gray-500">{m.idpAuthoritativeDescription()}</span>
			</span>
		</label>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<label class="flex flex-col gap-1">
				<span class="text-sm font-medium">{m.oidcGroupsClaim()}</span>
				<input
					type="text"
					name="oidc_groups_claim"
					class="input text-sm"
					bind:value={cfg.oidc_groups_claim}
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-sm font-medium">{m.samlGroupsAttribute()}</span>
				<input
					type="text"
					name="saml_groups_attribute"
					class="input text-sm"
					bind:value={cfg.saml_groups_attribute}
				/>
			</label>
		</div>

		<div class="flex justify-end">
			<button type="submit" class="btn btn-sm preset-filled-primary-500" disabled={savingCfg}>
				<i class="fa-solid fa-floppy-disk mr-1"></i>
				{m.save()}
			</button>
		</div>
	</form>

	<div class="flex items-center justify-between">
		<h3 class="text-base font-semibold flex items-center gap-2">
			<i class="fa-solid fa-arrows-left-right text-sm text-primary-500"></i>
			{m.idpGroupMappings()}
		</h3>
		<button class="btn btn-sm preset-filled-primary-500" onclick={modalCreateForm}>
			<i class="fa-solid fa-plus mr-1"></i>
			{m.createIdpGroupMapping()}
		</button>
	</div>

	{#if data.idpGroupMappings?.length > 0}
		<div class="card bg-white shadow overflow-hidden">
			<table class="table w-full text-sm">
				<thead class="bg-surface-50">
					<tr>
						<th class="px-4 py-2 text-left font-medium text-gray-600">{m.externalGroupId()}</th>
						<th class="px-4 py-2 text-left font-medium text-gray-600">{m.userGroup()}</th>
						<th class="px-4 py-2"></th>
					</tr>
				</thead>
				<tbody>
					{#each data.idpGroupMappings as mapping, i}
						{#if i > 0}
							<tr><td colspan="3"><hr class="border-surface-100" /></td></tr>
						{/if}
						<tr>
							<td class="px-4 py-2 font-mono text-xs">{mapping.external_group_id}</td>
							<td class="px-4 py-2">{mapping.user_group?.str ?? mapping.user_group}</td>
							<td class="px-4 py-2 text-right">
								<button
									aria-label={m.delete()}
									class="btn btn-sm preset-filled-error-500 cursor-pointer"
									data-testid="tablerow-delete-button"
									onclick={() => modalConfirmDelete(mapping.id, mapping)}
								>
									<i class="fa-solid fa-trash text-xs"></i>
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<p class="text-gray-400 text-sm italic">{m.noIdpGroupMappings()}</p>
	{/if}
</div>
