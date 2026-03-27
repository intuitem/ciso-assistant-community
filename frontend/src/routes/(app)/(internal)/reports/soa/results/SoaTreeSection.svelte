<script lang="ts">
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		nodeId: string;
		node: Record<string, any>;
		depth?: number;
		index?: number;
	}

	let { nodeId, node, depth = 0, index = 0 }: Props = $props();

	let expanded: boolean = $state(true);

	const children = $derived(Object.entries(node.children || {}));
	const hasChildren = $derived(children.length > 0);
	const isAssessable = $derived(node.assessable && node.ra_id);
	const returnUrl = $derived(page.url.pathname + page.url.search);
	const editHref = $derived(
		node.ra_id
			? `/requirement-assessments/${node.ra_id}/edit?next=${encodeURIComponent(returnUrl)}`
			: ''
	);
	const isNotApplicable = $derived(node.selected === false || node.result === 'not_applicable');

	function getStatusBadge(status: string): { label: string; classes: string } {
		switch (status) {
			case 'active':
				return { label: m.active(), classes: 'bg-green-100 text-green-700' };
			case 'in_progress':
				return { label: m.inProgress(), classes: 'bg-blue-100 text-blue-700' };
			case 'on_hold':
				return { label: m.onHold(), classes: 'bg-yellow-100 text-yellow-700' };
			case 'deprecated':
				return { label: m.deprecated(), classes: 'bg-red-100 text-red-700' };
			case 'to_do':
				return { label: m.toDo(), classes: 'bg-gray-100 text-gray-600' };
			default:
				return { label: status || '--', classes: 'bg-gray-100 text-gray-600' };
		}
	}

	const uniqueAppliedControls = $derived(
		(node.applied_controls || []).filter(
			(ac: Record<string, any>, i: number, self: Record<string, any>[]) =>
				self.findIndex((c: Record<string, any>) => c.id === ac.id) === i
		)
	);

	// Visual weight by depth: top-level sections are bold, deeper ones lighter
	const sectionStyles = $derived.by(() => {
		if (depth === 0) return 'bg-gray-700 text-white border-b-2 border-gray-800';
		if (depth === 1) return 'bg-gray-200 text-gray-900 border-b border-gray-300';
		return 'bg-gray-100 text-gray-700 border-b border-gray-200';
	});

	const sectionTextSize = $derived(depth === 0 ? 'text-sm font-bold' : 'text-sm font-semibold');
</script>

{#if isAssessable}
	<!-- Leaf row -->
	<tr
		class="border-b border-gray-200 transition-colors print:break-inside-avoid
			{isNotApplicable ? 'bg-gray-50 text-gray-400' : index % 2 === 0 ? 'bg-white' : 'bg-slate-50'}"
	>
		<!-- Ref -->
		<td
			class="px-3 py-2 text-xs font-mono whitespace-nowrap align-top {isNotApplicable
				? 'text-gray-400'
				: 'text-gray-600'}"
		>
			<span style="padding-left: {depth * 1}rem">{node.ref_id || ''}</span>
		</td>
		<!-- Requirement -->
		<td
			class="px-3 py-2 text-sm align-top overflow-hidden {isNotApplicable
				? 'text-gray-400'
				: 'text-gray-900'}"
		>
			{#if editHref}
				<Anchor breadcrumbAction="push" href={editHref} class="hover:underline">
					<span class="font-medium">{node.name || ''}</span>
				</Anchor>
			{:else}
				<div class="font-medium">{node.name || ''}</div>
			{/if}
			{#if node.description}
				<div class="text-xs mt-0.5 {isNotApplicable ? 'text-gray-300' : 'text-gray-500'}">
					{node.description}
				</div>
			{/if}
		</td>
		<!-- Applicable -->
		<td class="px-3 py-2 text-center align-top">
			{#if isNotApplicable}
				<span
					class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-700 border border-red-200"
				>
					{m.no()}
				</span>
			{:else}
				<span
					class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-700 border border-green-200"
				>
					{m.yes()}
				</span>
			{/if}
		</td>
		<!-- Observation -->
		<td
			class="px-3 py-2 text-sm align-top overflow-hidden {isNotApplicable
				? 'text-gray-400'
				: 'text-gray-600'}"
		>
			{#if isNotApplicable && !node.observation}
				<span class="inline-flex items-center gap-1 text-xs text-amber-600 print:text-amber-800">
					<i class="fas fa-exclamation-triangle text-[10px]"></i>
					{m.observationMissing()}
				</span>
			{:else}
				<span class="break-words">{node.observation || ''}</span>
			{/if}
		</td>
		<!-- Implementation -->
		<td class="px-3 py-2 align-top">
			{#if uniqueAppliedControls.length > 0}
				<div class="flex flex-col gap-2.5">
					{#each uniqueAppliedControls as ac}
						{@const statusBadge = getStatusBadge(ac.status)}
						<Anchor
							breadcrumbAction="push"
							href="/applied-controls/{ac.id}?next={encodeURIComponent(returnUrl)}"
							class="flex items-start gap-1.5 hover:underline"
						>
							<span
								class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium whitespace-nowrap flex-shrink-0 {statusBadge.classes}"
							>
								{statusBadge.label}
							</span>
							<span class="text-xs text-gray-700 break-words">
								{ac.ref_id ? `${ac.ref_id} ` : ''}{ac.name}
							</span>
						</Anchor>
					{/each}
				</div>
			{:else}
				<span class="text-xs text-gray-300">--</span>
			{/if}
		</td>
	</tr>
{:else if hasChildren}
	<!-- Section header -->
	<tr class="{sectionStyles} print:break-inside-avoid print:break-after-avoid">
		<td colspan={5} class="px-3 py-2">
			<button
				onclick={() => (expanded = !expanded)}
				class="flex items-center gap-2.5 w-full text-left"
				style="padding-left: {depth * 1}rem"
			>
				<i
					class="fas fa-chevron-right text-xs transition-transform duration-200 print:hidden
						{depth === 0 ? 'text-gray-400' : 'text-gray-500'}
						{expanded ? 'rotate-90' : ''}"
				></i>
				<span class={sectionTextSize}>
					{#if node.ref_id}
						<span class="{depth === 0 ? 'text-gray-300' : 'text-gray-500'} font-mono mr-1.5"
							>{node.ref_id}</span
						>
					{/if}
					{node.name || ''}
				</span>
			</button>
		</td>
	</tr>
	{#if expanded}
		{#each children as [childId, childNode], i}
			<svelte:self nodeId={childId} node={childNode} depth={depth + 1} index={i} />
		{/each}
	{/if}
{/if}
