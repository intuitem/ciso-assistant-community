<script lang="ts">
	import { goto, invalidateAll, preloadData, pushState } from '$app/navigation';
	import { page } from '$app/stores';
	import { deserialize } from '$app/forms';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';
	import AuditTableMode from '../../../(third-party)/compliance-assessments/[id=uuid]/table-mode/+page.svelte';
	import TreeView from '$lib/components/TreeView/TreeView.svelte';
	import TreeViewItem from '$lib/components/TreeView/TreeViewItem.svelte';
	import type { Actions, PageData } from './$types';

	interface Props {
		data: PageData;
		form: Actions;
	}

	let { data, form }: Props = $props();

	const mailing =
		Boolean(data.data.compliance_assessment) && Boolean(data.data.representatives.length);

	const reviewAssignments = $derived(data.reviewAssignments ?? []);
	const reviewHref = $derived(
		reviewAssignments.length === 1
			? `/auditee-assessments/${reviewAssignments[0].id}`
			: `/compliance-assessments/${data.data.compliance_assessment?.id}/assignments`
	);

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();
	let isCloning = $state(false);

	function handleClone() {
		modalStore.trigger({
			type: 'prompt',
			title: m.newRevision(),
			body: m.newRevisionHelpText(),
			value: `${data.data.name} (copy)`,
			valueAttr: { required: true },
			response: async (name: string | false) => {
				if (name === false || !`${name ?? ''}`.trim()) return;
				isCloning = true;
				try {
					const body = new FormData();
					body.set('name', `${name}`.trim());
					const res = await fetch('?/clone', { method: 'POST', body });
					const result = deserialize(await res.text());
					const cloned = (result.type === 'success' ? result.data : null) as {
						cloneStatus?: number;
						cloneBody?: { id?: string; error?: string };
					} | null;
					if (cloned?.cloneStatus === 201) {
						await invalidateAll();
						goto(`/entity-assessments/${cloned.cloneBody?.id}`);
					} else {
						toastStore.trigger({
							message: cloned?.cloneBody?.error || m.anErrorOccurred(),
							background: 'preset-filled-error-500',
							timeout: 5000
						});
					}
				} finally {
					isCloning = false;
				}
			}
		});
	}
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<DetailView {data} {mailing}>
		{#snippet actions()}
			{#if data.data.compliance_assessment}
				<button
					class="btn preset-filled-secondary-500 h-fit"
					onclick={handleClone}
					disabled={isCloning}
					data-testid="clone-assessment-button"
				>
					<i class="fa-solid fa-copy mr-2"></i>{m.newRevision()}
				</button>
			{/if}
			{#if reviewAssignments.length > 0}
				<a href={reviewHref} class="btn preset-filled-secondary-500 h-fit">
					<i class="fa-solid fa-clipboard-check mr-2"></i>{m.reviewResponses()}
				</a>
			{/if}
		{/snippet}
	</DetailView>
	{#if data.data.compliance_assessment}
		<div class="card px-6 py-4 bg-surface-50-950 flex flex-row justify-between shadow-lg w-full">
			<TreeView>
				<TreeViewItem
					alwaysDisplayCaret={true}
					caretOpen=""
					caretClosed="-rotate-90"
					onToggle={async () => {
						const href = `/compliance-assessments/${data.data.compliance_assessment.id}/table-mode`;
						const result = await preloadData(href);
						if (result.type === 'loaded' && result.status === 200) {
							pushState('', { auditTableMode: result.data });
						} else {
							// Something went wrong, try navigating
							goto(href);
						}
					}}
				>
					<span class="font-semibold text-lg select-none">{m.questionnaire()}</span>
					{#snippet childrenSlot()}
						{#if Object.hasOwn($page?.state, 'auditTableMode')}
							<div class="max-h-192 overflow-y-scroll">
								<AuditTableMode
									{form}
									data={$page?.state?.auditTableMode}
									actionPath={`/compliance-assessments/${data.data.compliance_assessment.id}/table-mode`}
									shallow
									questionnaireOnly
									invalidateAll={false}
								/>
							</div>
						{/if}
					{/snippet}
				</TreeViewItem>
			</TreeView>
		</div>
	{/if}
</div>
