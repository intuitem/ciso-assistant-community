<script lang="ts">
	import { m } from '$paraglide/messages';
	import WorkflowCanvas from './WorkflowCanvas.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const readonly = $derived(data.activeVersion.status !== 'draft');

	const STATUS_BADGE: Record<string, { class: string; label: () => string }> = {
		draft: { class: 'preset-tonal-warning', label: () => m.draftVersion() },
		published: { class: 'preset-tonal-success', label: () => m.publishedVersion() },
		archived: { class: 'preset-tonal', label: () => m.archivedVersion() }
	};
	const badge = $derived(STATUS_BADGE[data.activeVersion.status] ?? STATUS_BADGE.archived);
</script>

<div class="flex flex-col h-[calc(100vh-7.5rem)] gap-3">
	<div class="flex items-center gap-3 shrink-0">
		<h1 class="text-lg font-semibold text-surface-900-100">{data.workflow.name}</h1>
		<span class="badge {badge.class} text-xs" data-testid="version-badge">
			v{data.activeVersion.version_number} · {badge.label()}
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
				{readonly}
				roles={data.roles}
				actors={data.actors}
				taskTemplates={data.taskTemplates}
				subprocessCandidates={data.subprocessCandidates}
				creatableModels={data.creatableModels}
				fkOptions={data.fkOptions}
				hookUrl={data.hookUrl}
			/>
		{/key}
	</div>
</div>
