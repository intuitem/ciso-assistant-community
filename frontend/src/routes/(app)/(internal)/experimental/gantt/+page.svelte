<script lang="ts">
	import type { PageData } from './$types';
	import GanttChart from '$lib/components/Gantt/GanttChart.svelte';
	import type { GanttEntry, Folder } from '$lib/components/Gantt/GanttChart.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const OBJECT_TYPES = [
		{
			key: 'appliedControls',
			label: 'Applied Controls',
			prefix: 'control',
			urlPath: 'applied-controls'
		},
		{ key: 'taskNodes', label: 'Tasks', prefix: 'task', urlPath: 'task-nodes' },
		{
			key: 'complianceAssessments',
			label: 'Compliance Assessments',
			prefix: 'compliance',
			urlPath: 'compliance-assessments'
		},
		{
			key: 'riskAssessments',
			label: 'Risk Assessments',
			prefix: 'risk',
			urlPath: 'risk-assessments'
		},
		{
			key: 'businessImpactAnalyses',
			label: 'Business Impact Analysis',
			prefix: 'bia',
			urlPath: 'resilience/business-impact-analysis'
		},
		{
			key: 'organisationObjectives',
			label: 'Organisation Objectives',
			prefix: 'objective',
			urlPath: 'organisation-objectives'
		},
		{
			key: 'findingsAssessments',
			label: 'Findings Assessments',
			prefix: 'findings',
			urlPath: 'findings-assessments'
		}
	] as const;

	type ObjectTypeKey = (typeof OBJECT_TYPES)[number]['key'];

	let selectedTypes = $state<Set<ObjectTypeKey>>(new Set(['appliedControls', 'taskNodes']));
	let pendingTypes = $state<Set<ObjectTypeKey>>(new Set(['appliedControls', 'taskNodes']));

	function toggleType(key: ObjectTypeKey) {
		const newSet = new Set(pendingTypes);
		if (newSet.has(key)) {
			newSet.delete(key);
		} else {
			newSet.add(key);
		}
		pendingTypes = newSet;
	}

	function applySelection() {
		selectedTypes = new Set(pendingTypes);
	}

	function transformToGanttEntry(item: any, prefix: string): GanttEntry | null {
		let start_date = item.start_date || null;
		let end_date = item.eta || item.end_date || item.due_date || item.target_date || null;

		if (!start_date && !end_date) return null;

		let type: 'milestone' | 'task' | 'activity' = 'milestone';
		if (start_date && end_date) {
			type = 'activity';
		} else if (prefix === 'task') {
			type = 'task';
			end_date = end_date || start_date;
			start_date = null;
		} else {
			end_date = end_date || start_date;
			start_date = null;
		}

		let progress = 0;
		if (item.status === 'active' || item.status === 'done' || item.status === 'completed') {
			progress = 100;
		} else if (item.status === 'in_progress') {
			progress = 50;
		}

		return {
			id: `${prefix}-${item.id}`,
			name: item.name || item.title || 'Unnamed',
			type,
			start_date,
			end_date,
			progress,
			description: item.description || '',
			ref_id: item.ref_id || '',
			folder_uuid: item.folder?.id || '',
			group_id: item.category || null
		};
	}

	function transformDataToEntries(dataKey: ObjectTypeKey): GanttEntry[] {
		const items = data[dataKey] || [];
		const typeConfig = OBJECT_TYPES.find((t) => t.key === dataKey);
		if (!typeConfig) return [];

		return items
			.map((item: any) => transformToGanttEntry(item, typeConfig.prefix))
			.filter((entry: GanttEntry | null): entry is GanttEntry => entry !== null);
	}

	let ganttEntries = $derived(
		Array.from(selectedTypes).flatMap((key) => transformDataToEntries(key))
	);

	let folders: Folder[] = $derived(
		data.folders.map((f: any) => ({
			id: f.id,
			name: f.name,
			str: f.str
		}))
	);

	function itemUrlBuilder(entry: GanttEntry): string {
		for (const typeConfig of OBJECT_TYPES) {
			if (entry.id.startsWith(`${typeConfig.prefix}-`)) {
				const id = entry.id.replace(`${typeConfig.prefix}-`, '');
				return `/${typeConfig.urlPath}/${id}`;
			}
		}
		return '#';
	}

	let hasChanges = $derived(
		pendingTypes.size !== selectedTypes.size ||
			![...pendingTypes].every((t) => selectedTypes.has(t))
	);
</script>

<div class="bg-white p-6 shadow-sm space-y-4">
	<div>
		<h2 class="h2 font-bold">Gantt Diagram</h2>
		<p class="text-sm text-gray-600">Visualize timeline across multiple object types</p>
	</div>

	<!-- Object Type Selection Panel -->
	<div class="bg-gray-50 p-4 rounded-lg border border-gray-200">
		<div class="flex items-center justify-between mb-3">
			<span class="font-medium text-sm text-gray-700">Select Object Types</span>
			<button
				type="button"
				class="btn btn-sm preset-filled"
				onclick={applySelection}
				disabled={!hasChanges}
			>
				Apply
			</button>
		</div>
		<div class="flex flex-wrap gap-4">
			{#each OBJECT_TYPES as typeConfig}
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="checkbox"
						checked={pendingTypes.has(typeConfig.key)}
						onchange={() => toggleType(typeConfig.key)}
						class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
					/>
					<span class="text-sm text-gray-700">{typeConfig.label}</span>
				</label>
			{/each}
		</div>
	</div>

	<!-- Gantt Chart Component -->
	<GanttChart entries={ganttEntries} {folders} {itemUrlBuilder} />
</div>
