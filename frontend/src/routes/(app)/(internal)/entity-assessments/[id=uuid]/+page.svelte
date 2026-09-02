<script lang="ts">
	import { goto, invalidateAll, preloadData, pushState } from '$app/navigation';
	import { page } from '$app/stores';
	import { deserialize } from '$app/forms';
	import { getModalStore, type ModalStore } from '$lib/components/Modals/stores';
	import NewRevisionModal from '$lib/components/Modals/NewRevisionModal.svelte';
	import RingProgress from '$lib/components/DataViz/RingProgress.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ModalComponent, ModalSettings } from '$lib/components/Modals/stores';
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

	async function createRevision(values: { name: string; version: string }) {
		isCloning = true;
		try {
			const body = new FormData();
			body.set('name', values.name);
			body.set('version', values.version);
			const res = await fetch('?/clone', { method: 'POST', body });
			const result = deserialize(await res.text());
			const cloned = (result.type === 'success' ? result.data : null) as {
				cloneStatus?: number;
				cloneBody?: { id?: string; error?: string; name?: string[]; version?: string[] };
			} | null;
			if (cloned?.cloneStatus === 201) {
				await invalidateAll();
				goto(`/entity-assessments/${cloned.cloneBody?.id}`);
			} else {
				const body = cloned?.cloneBody;
				toastStore.trigger({
					message: body?.error || body?.name?.[0] || body?.version?.[0] || m.anErrorOccurred(),
					background: 'preset-filled-error-500',
					timeout: 5000
				});
			}
		} finally {
			isCloning = false;
		}
	}

	function handleClone() {
		const modalComponent: ModalComponent = {
			ref: NewRevisionModal,
			props: {
				initialName: data.data.name,
				initialVersion: data.data.version ?? '1.0',
				onSubmit: createRevision
			}
		};
		const modal: ModalSettings = { type: 'component', component: modalComponent };
		modalStore.trigger(modal);
	}
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<DetailView {data} {mailing}>
		{#snippet widgets()}
			{#if data.data.compliance_assessment}
				<div class="flex flex-col h-full justify-center items-center gap-4 p-2">
					<div class="flex flex-row justify-center gap-6">
						<div class="flex flex-col items-center w-32">
							<span class="text-xs text-surface-600-400">{m.completion()}</span>
							<RingProgress
								name="ea_completion"
								value={data.data.completion ?? 0}
								max={100}
								isPercentage
								strokeWidth={26}
								fontSize={26}
								color="#6366f1"
							/>
						</div>
						<div class="flex flex-col items-center w-32">
							<!-- The table's wording: `reviewProgress` renders as just "Progress". -->
							<span class="text-xs text-surface-600-400">{m.auditReviewProgress()}</span>
							<RingProgress
								name="ea_review"
								value={data.data.review_progress ?? 0}
								max={100}
								isPercentage
								strokeWidth={26}
								fontSize={26}
								color="#10b981"
							/>
						</div>
					</div>
					<div class="flex flex-col items-center gap-1 text-xs">
						{#if data.data.assignment_status}
							<span class="text-surface-600-400">{m.assignmentStatus()}</span>
							<span class="badge preset-tonal-secondary">
								{safeTranslate(data.data.assignment_status)}
							</span>
						{/if}
					</div>
				</div>
			{/if}
		{/snippet}
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
