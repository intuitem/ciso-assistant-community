<script lang="ts">
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { page } from '$app/state';
	import { formatDate } from '$lib/utils/datetime';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const idSchema = zod(z.object({ id: z.string() }));

	function pageHref(target: number): string {
		const params = new URLSearchParams(page.url.searchParams);
		params.set('page', String(target));
		return `?${params}`;
	}

	function confirmProps(id: string, formAction: string) {
		return { _form: defaults({ id }, idSchema), schema: idSchema, id, formAction, debug: false };
	}

	function modalRevoke(row: any): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: confirmProps(`${row.user.id}:${row.client_id}`, '?/revoke')
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.confirmModalTitle(),
			body: m.connectedAppRevokeUserConfirm({ name: row.name, email: row.user.email })
		};
		modalStore.trigger(modal);
	}

	async function modalRevokeForEveryone(row: any): Promise<void> {
		const res = await fetch(`/connected-apps/apps/${row.client_id}`);
		if (!res.ok) return;
		const group = await res.json();
		const body = [
			m.connectedAppRevokeGroupConfirm({
				users: group.users,
				registrations: group.registrations,
				hosts: group.redirect_hosts.join(', ')
			}),
			group.self_registered ? m.connectedAppRevokeGroupDeletes() : ''
		]
			.filter(Boolean)
			.join('\n\n');
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal,
			props: confirmProps(row.client_id, '?/revokeGroup')
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.connectedAppRevokeGroupTitle({ name: group.name }),
			body
		};
		modalStore.trigger(modal);
	}
</script>

<div class="card bg-white shadow-sm p-4 space-y-4">
	<p class="text-sm text-surface-700-300">{m.connectedAppsAdminDescription()}</p>

	<form method="GET" class="flex flex-wrap items-center gap-3" data-testid="connected-apps-filters">
		<input
			type="search"
			name="search"
			value={data.search}
			placeholder={m.connectedAppsSearch()}
			class="input max-w-md"
		/>
		<button type="submit" class="btn preset-filled-primary-500">
			<i class="fa-solid fa-filter mr-2"></i>{m.filters()}
		</button>
	</form>

	{#if data.connections.length === 0}
		<p class="text-sm text-surface-600-400">{m.noConnectedAppsAdmin()}</p>
	{:else}
		<table class="table-auto w-full text-sm" data-testid="admin-connected-apps-table">
			<thead>
				<tr class="text-left border-b border-surface-200-800">
					<th class="py-2 pr-4">{m.user()}</th>
					<th class="py-2 pr-4">{m.connectedAppName()}</th>
					<th class="py-2 pr-4">{m.connectedAppRedirectsTo()}</th>
					<th class="py-2 pr-4">{m.connectedAppAllowedActions()}</th>
					<th class="py-2 pr-4">{m.connectedAppAuthorized()}</th>
					<th class="py-2 pr-4">{m.connectedAppLastUsed()}</th>
					<th class="py-2"></th>
				</tr>
			</thead>
			<tbody>
				{#each data.connections as row (`${row.user.id}:${row.client_id}`)}
					<tr class="border-b border-surface-100-900 align-top">
						<td class="py-2 pr-4">{row.user.email}</td>
						<td class="py-2 pr-4">
							<p class="font-medium">{row.name}</p>
						</td>
						<td class="py-2 pr-4">
							{#each row.redirect_hosts as host}
								<code class="block">{host}</code>
							{/each}
						</td>
						<td class="py-2 pr-4">
							{#if row.profile}
								<ul class="list-disc list-inside">
									{#each row.profile.actions as action}
										<li>{safeTranslate(action)}</li>
									{/each}
								</ul>
							{:else}
								<span class="text-surface-600-400">--</span>
							{/if}
						</td>
						<td class="py-2 pr-4">
							{#if row.authorized_at}
								{formatDate(new Date(row.authorized_at), false, getLocale())}
							{:else}
								<span class="text-surface-600-400">--</span>
							{/if}
						</td>
						<td class="py-2 pr-4">
							{#if row.last_used_at}
								{formatDate(new Date(row.last_used_at), true, getLocale())}
							{:else}
								<span class="text-surface-600-400">{m.connectedAppNeverUsed()}</span>
							{/if}
						</td>
						<td class="py-2 whitespace-nowrap">
							<button
								onclick={() => modalRevoke(row)}
								aria-label={m.revokeConnectedApp()}
								title={m.revokeConnectedApp()}
								class="cursor-pointer hover:text-error-500 mr-3"
								data-testid="admin-connected-app-revoke-button"
								><i class="fa-solid fa-trash"></i></button
							>
							<button
								onclick={() => modalRevokeForEveryone(row)}
								aria-label={m.revokeConnectedAppForEveryone()}
								title={m.revokeConnectedAppForEveryone()}
								class="cursor-pointer hover:text-error-500"
								data-testid="admin-connected-app-revoke-all-button"
								><i class="fa-solid fa-users-slash"></i></button
							>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
		{#if data.pageCount > 1}
			<nav
				class="flex items-center justify-end gap-3 text-sm"
				data-testid="connected-apps-pagination"
			>
				<a
					href={pageHref(data.pageNumber - 1)}
					class="btn preset-outlined-surface-500"
					class:pointer-events-none={data.pageNumber <= 1}
					class:opacity-50={data.pageNumber <= 1}>{m.previous()}</a
				>
				<span>{data.pageNumber} / {data.pageCount}</span>
				<a
					href={pageHref(data.pageNumber + 1)}
					class="btn preset-outlined-surface-500"
					class:pointer-events-none={data.pageNumber >= data.pageCount}
					class:opacity-50={data.pageNumber >= data.pageCount}>{m.next()}</a
				>
			</nav>
		{/if}
	{/if}
</div>
