<script lang="ts">
	import { m } from '$paraglide/messages';
	import WorkflowCanvas from './WorkflowCanvas.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// Published versions are directly editable: the canvas silently clones them
	// into a draft on the first change and reports it here so the badge follows.
	const readonly = $derived(data.activeVersion.status === 'archived');

	let liveDraft = $state<{ id: string; version_number: number } | null>(null);
	$effect(() => {
		void data.activeVersion.id;
		liveDraft = null;
	});
	const displayVersion = $derived(
		liveDraft ? { version_number: liveDraft.version_number, status: 'draft' } : data.activeVersion
	);

	const STATUS_BADGE: Record<string, { class: string; label: () => string }> = {
		draft: { class: 'preset-tonal-warning', label: () => m.draftVersion() },
		published: { class: 'preset-tonal-success', label: () => m.publishedVersion() },
		archived: { class: 'preset-tonal', label: () => m.archivedVersion() }
	};
	const badge = $derived(STATUS_BADGE[displayVersion.status] ?? STATUS_BADGE.archived);
</script>

<div class="flex flex-col h-[calc(100vh-7.5rem)] gap-3">
	<div class="flex items-center gap-3 shrink-0">
		<h1 class="text-lg font-semibold text-surface-900-100">{data.workflow.name}</h1>
		<span class="badge {badge.class} text-xs" data-testid="version-badge">
			v{displayVersion.version_number} · {badge.label()}
		</span>
		{#if data.workflow.description}
			<p class="text-sm text-surface-600-400 truncate">{data.workflow.description}</p>
		{/if}
	</div>

	<div class="flex-1 min-h-0">
		{#key data.activeVersion.id + data.activeVersion.status}
			<WorkflowCanvas
				graph={data.graph}
				workflowId={data.workflow.id}
				versionId={data.activeVersion.id}
				versionStatus={data.activeVersion.status}
				folderId={data.workflow.folder.id}
				{readonly}
				roles={data.roles}
				actors={data.actors}
				taskTemplates={data.taskTemplates}
				subprocessCandidates={data.subprocessCandidates}
				creatableModels={data.creatableModels}
				fkOptions={data.fkOptions}
				onDraftCreated={(draft) => (liveDraft = draft)}
			/>
		{/key}
	</div>
</div>
