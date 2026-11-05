<script lang="ts">
	import WorkflowCanvas from './WorkflowCanvas.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// Published versions are directly editable: the canvas silently clones them
	// into a draft on the first change and tracks the badge itself.
	const readonly = $derived(data.activeVersion.status === 'archived');
	// A draft can be discarded only when a published version exists to fall
	// back to. Loading a published version implies one exists, so this also
	// covers the auto-drafted (ensureDraft) case without re-deriving.
	const hasPublishedFallback = $derived(
		data.versions.some((v: { status: string }) => v.status === 'published')
	);

	// Discarding an AUTO-DRAFTED draft is invisible to page data (it loaded the
	// published version and never learned about the draft), so the {#key} below
	// wouldn't change and the stale canvas would keep editing a deleted version.
	// The canvas bumps this epoch after a discard to force its own remount.
	let canvasEpoch = $state(0);

	// The appbar height varies (breadcrumbs, optional description lines), so a
	// hardcoded calc() either overflows or leaves a gap. Measure the space left
	// between the container's top edge and the viewport bottom instead, minus
	// the parent <main>'s bottom padding so the canvas ends flush with the page.
	let container = $state<HTMLDivElement | null>(null);
	let canvasHeight = $state<number | null>(null);

	function measure() {
		if (!container) return;
		const paddingBottom = container.parentElement
			? parseFloat(getComputedStyle(container.parentElement).paddingBottom)
			: 0;
		const top = container.getBoundingClientRect().top;
		canvasHeight = Math.max(400, window.innerHeight - top - paddingBottom);
	}

	$effect(() => {
		measure();
	});
</script>

<svelte:window onresize={measure} />

<div
	bind:this={container}
	class="h-[calc(100vh-12rem)]"
	style:height={canvasHeight === null ? undefined : `${canvasHeight}px`}
>
	{#key data.activeVersion.id + data.activeVersion.status + canvasEpoch}
		<WorkflowCanvas
			workflowName={data.workflow.name}
			workflowDescription={data.workflow.description}
			initialVersionNumber={data.activeVersion.version_number}
			graph={data.graph}
			workflowId={data.workflow.id}
			versionId={data.activeVersion.id}
			versionStatus={data.activeVersion.status}
			{readonly}
			{hasPublishedFallback}
			taskTemplates={data.taskTemplates}
			subprocessCandidates={data.subprocessCandidates}
			creatableModels={data.creatableModels}
			updatableModels={data.updatableModels}
			readableModels={data.readableModels}
			workflowIsActive={data.workflow.is_active}
			workflowTimeoutSeconds={data.workflow.timeout_seconds}
			versions={data.versions}
			versionPinned={data.versionPinned}
			fkOptions={data.fkOptions}
			onDiscarded={() => (canvasEpoch += 1)}
		/>
	{/key}
</div>
