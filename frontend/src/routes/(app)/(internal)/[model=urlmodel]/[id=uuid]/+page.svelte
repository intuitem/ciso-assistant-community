<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import CommentsPanel from '$lib/components/CommentsPanel/CommentsPanel.svelte';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { safeTranslate } from '$lib/utils/i18n';
	import { openEntityPicker } from '$lib/utils/entityPicker';
	import { canPerformAction } from '$lib/utils/access-control';
	import { invalidateAll } from '$app/navigation';
	import type { PageData, ActionData } from './$types';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	// User-group membership is the reverse side of User.user_groups. Managing it from
	// the group's detail page PATCHes the group's `users` field — gated by
	// change_usergroup on the group's folder — so a domain manager can add/remove
	// members without write access on the (Global-scoped) User object.
	const canManageMembers = $derived(
		Boolean(
			data.model.name === 'usergroup' &&
				canPerformAction({
					user: page.data.user,
					action: 'change',
					model: 'usergroup',
					domain: data.data.folder?.id ?? data.data.folder ?? page.data.user.root_folder_id
				})
		)
	);

	function addMembers(): void {
		const groupId = data.data.id;
		openEntityPicker(modalStore, {
			endpoint: 'users',
			title: m.addMembers(),
			subtitle: data.data.name ?? data.data.str,
			labelField: 'email',
			secondaryField: 'str',
			activeField: 'is_active',
			// Add-only: exclude users already in the group so the picker only ever
			// lists candidates to add. Removal is a batch action on the Users tab.
			scopeFilters: { exclude_user_groups: groupId },
			confirmLabel: m.addMembers(),
			async onConfirm(ids: string[]) {
				if (!ids.length) return;
				const res = await fetch(`/user-groups/${groupId}/add-members`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ users: ids })
				});
				if (!res.ok) {
					const body = await res.json().catch(() => ({}));
					toastStore.trigger({
						message:
							typeof body?.error === 'string' ? safeTranslate(body.error) : m.anErrorOccurred(),
						background: 'preset-filled-error-500'
					});
					// Throw so the picker keeps the selection and surfaces the failure
					// instead of closing as if it succeeded.
					throw new Error('Failed to add members');
				}
				await invalidateAll();
				toastStore.trigger({
					message: m.membersAdded(),
					background: 'preset-filled-success-500'
				});
			}
		});
	}
</script>

{#if canManageMembers}
	<div class="flex items-center justify-end mb-4">
		<button
			type="button"
			class="btn preset-filled-primary-500"
			data-testid="add-members-button"
			onclick={addMembers}
		>
			<i class="fa-solid fa-user-plus mr-2"></i>{m.addMembers()}
		</button>
	</div>
{/if}

{#if data.model.name === 'fearedevent'}
	<div class="flex items-center justify-between mb-4">
		<Anchor
			breadcrumbAction="push"
			href={`/ebios-rm/${data.data.ebios_rm_study.id}`}
			class="flex items-center space-x-2 text-primary-800-200 hover:text-primary-600-400"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<p>{m.goBackToEbiosRmStudy()}</p>
		</Anchor>
	</div>
{/if}

<DetailView {data} />

{#if data.model.name === 'finding' && page.data?.featureflags?.comments}
	<div class="mt-4">
		<CommentsPanel parentType="finding" parentId={data.data.id} />
	</div>
{/if}

{#if data.model.name == 'requirementmappingset' && data.data.frameworks_available}
	<div class="card my-4 p-4 bg-surface-50-950">
		<span class="bg-purple-700 text-white px-2 py-1 rounded-sm text-sm font-semibold">new</span><a
			class="ml-2 hover:text-purple-700"
			href={`/experimental/mapping/${data.data.id}`}>{m.viewOnGraphExplorer()}</a
		>
	</div>
{/if}
