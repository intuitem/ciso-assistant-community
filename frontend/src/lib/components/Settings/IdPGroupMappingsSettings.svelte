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
	import IdPGroupCreateModal from '../../../routes/(app)/(internal)/settings/idp-group-mappings/IdPGroupCreateModal.svelte';
	import { defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { IdPGroupSchema, IdPGroupMappingSchema } from '$lib/utils/schemas';
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

	// Group the routes (IdPGroupMapping rows) by their parent IdP group.
	const routesByGroup = $derived.by(() => {
		const map: Record<string, any[]> = {};
		for (const mapping of data.idpGroupMappings ?? []) {
			const groupId = mapping.idp_group?.id ?? mapping.idp_group;
			(map[groupId] ??= []).push(mapping);
		}
		return map;
	});

	function modalCreateIdpGroup(): void {
		const modalComponent: ModalComponent = {
			ref: IdPGroupCreateModal,
			props: {
				form: data.idpGroupCreateForm,
				formAction: '?/createIdpGroup',
				invalidateAll: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.createIdpGroup()
		};
		modalStore.trigger(modal);
	}

	function modalEditIdpGroup(group: any): void {
		const modalComponent: ModalComponent = {
			ref: IdPGroupCreateModal,
			props: {
				form: defaults(
					{ id: group.id, external_group_id: group.external_group_id },
					zod(IdPGroupSchema)
				),
				formAction: '?/updateIdpGroup',
				invalidateAll: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.editIdpGroup()
		};
		modalStore.trigger(modal);
	}

	function modalConfirmDeleteIdpGroup(group: any): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: defaults({ id: group.id }, zod(z.object({ id: z.string() }))),
				id: group.id,
				debug: false,
				URLModel: 'idp-groups',
				formAction: '?/deleteIdpGroup'
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.deleteModalTitle(),
			body: m.deleteModalMessage({ name: String(group.external_group_id ?? '') })
		};
		modalStore.trigger(modal);
	}

	function modalCreateRoute(group: any): void {
		const modalComponent: ModalComponent = {
			ref: IdPGroupMappingCreateModal,
			props: {
				form: defaults({ idp_group: group.id }, zod(IdPGroupMappingSchema)),
				formAction: '?/createIdpGroupMapping',
				idpGroupLocked: true,
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

	function modalConfirmDeleteRoute(mapping: any): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: defaults({ id: mapping.id }, zod(z.object({ id: z.string() }))),
				id: mapping.id,
				debug: false,
				URLModel: 'idp-group-mappings',
				formAction: '?/deleteIdpGroupMapping'
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.deleteModalTitle(),
			body: m.deleteModalMessage({ name: String(mapping.user_group?.str ?? '') })
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
			{m.idpGroups()}
		</h3>
		<button class="btn btn-sm preset-filled-primary-500" onclick={modalCreateIdpGroup}>
			<i class="fa-solid fa-plus mr-1"></i>
			{m.createIdpGroup()}
		</button>
	</div>

	{#if data.idpGroups?.length > 0}
		<div class="flex flex-col gap-3">
			{#each data.idpGroups as group}
				{@const routes = routesByGroup[group.id] ?? []}
				<div class="card bg-white shadow overflow-hidden">
					<div class="flex items-center justify-between px-4 py-3 bg-surface-50">
						<div class="flex items-center gap-2 min-w-0">
							<i class="fa-solid fa-users-rectangle text-sm text-primary-500"></i>
							<span class="font-mono text-sm truncate">{group.external_group_id}</span>
							{#if group.scim_external_id}
								<span class="badge preset-tonal-secondary text-xs" title={group.scim_external_id}
									>SCIM</span
								>
							{/if}
						</div>
						<div class="flex items-center gap-1 shrink-0">
							<button
								class="btn btn-sm preset-filled-primary-500 cursor-pointer"
								onclick={() => modalCreateRoute(group)}
							>
								<i class="fa-solid fa-plus text-xs mr-1"></i>
								{m.createIdpGroupMapping()}
							</button>
							<button
								aria-label={m.edit()}
								class="btn-icon btn-sm preset-tonal cursor-pointer"
								onclick={() => modalEditIdpGroup(group)}
							>
								<i class="fa-solid fa-pen text-xs"></i>
							</button>
							<button
								aria-label={m.delete()}
								class="btn-icon btn-sm preset-filled-error-500 cursor-pointer"
								data-testid="tablerow-delete-button"
								onclick={() => modalConfirmDeleteIdpGroup(group)}
							>
								<i class="fa-solid fa-trash text-xs"></i>
							</button>
						</div>
					</div>

					{#if routes.length > 0}
						<ul class="divide-y divide-surface-100">
							{#each routes as mapping}
								<li class="flex items-center justify-between px-4 py-2 text-sm">
									<span class="flex items-center gap-2">
										<i class="fa-solid fa-arrow-right text-xs text-gray-400"></i>
										{mapping.user_group?.str ?? mapping.user_group}
									</span>
									<button
										aria-label={m.delete()}
										class="btn-icon btn-sm preset-tonal-error cursor-pointer"
										onclick={() => modalConfirmDeleteRoute(mapping)}
									>
										<i class="fa-solid fa-xmark text-xs"></i>
									</button>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="px-4 py-3 text-gray-400 text-xs italic">{m.noIdpGroupMappings()}</p>
					{/if}
				</div>
			{/each}
		</div>
	{:else}
		<p class="text-gray-400 text-sm italic">{m.noIdpGroups()}</p>
	{/if}
</div>
