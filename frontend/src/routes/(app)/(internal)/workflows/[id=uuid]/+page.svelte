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
</script>

<div class="h-[calc(100vh-7.5rem)]">
	{#key data.activeVersion.id + data.activeVersion.status}
		<WorkflowCanvas
			workflowName={data.workflow.name}
			workflowDescription={data.workflow.description}
			initialVersionNumber={data.activeVersion.version_number}
			graph={data.graph}
			workflowId={data.workflow.id}
			versionId={data.activeVersion.id}
			versionStatus={data.activeVersion.status}
			folderId={data.workflow.folder.id}
			{readonly}
			{hasPublishedFallback}
			taskTemplates={data.taskTemplates}
			subprocessCandidates={data.subprocessCandidates}
			creatableModels={data.creatableModels}
			fkOptions={data.fkOptions}
		/>
	{/key}
</div>
