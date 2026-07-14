<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import CommentsPanel from '$lib/components/CommentsPanel/CommentsPanel.svelte';
	import SelectExistingModal from '$lib/components/Modals/SelectExistingModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { canPerformAction } from '$lib/utils/access-control';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { PageData, ActionData } from './$types';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	// User-group membership is the reverse side of User.user_groups. Managing it from
	// the group's detail page PATCHes the group's `users` field — gated by
	// change_usergroup on the group's folder — so a domain manager can add/remove
	// members without write access on the (Global-scoped) User object.
	const canManageMembers = $derived(
		Boolean(
			data.model.name === 'usergroup' &&
				data.updateForm &&
				canPerformAction({
					user: page.data.user,
					action: 'change',
					model: 'usergroup',
					domain: data.data.folder?.id ?? data.data.folder ?? page.data.user.root_folder_id
				})
		)
	);

	function manageMembers(): void {
		if (!data.updateForm) return;
		const modalComponent: ModalComponent = {
			ref: SelectExistingModal,
			props: {
				form: data.updateForm,
				urlModel: 'user-groups',
				field: 'users',
				optionsEndpoint: 'users',
				label: 'members',
				optionsExtraFields: [],
				// Users have no `name`; label them by their display string
				// (first/last name, or email as fallback).
				optionsLabelField: 'str',
				// Server-side search so the picker scales to very large user counts
				// instead of loading every user into the browser.
				lazy: true
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.manageMembers()
		};
		modalStore.trigger(modal);
	}
</script>

{#if canManageMembers}
	<div class="flex items-center justify-end mb-4">
		<button
			class="btn preset-filled-primary-500"
			data-testid="manage-members-button"
			onclick={manageMembers}
		>
			<i class="fa-solid fa-users mr-2"></i>{m.manageMembers()}
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
