<script lang="ts">
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		nodeId: string;
		node: Record<string, any>;
		depth?: number;
	}

	let { nodeId, node, depth = 0 }: Props = $props();

	let expanded: boolean = $state(true);

	const children = $derived(Object.entries(node.children || {}));
	const hasChildren = $derived(children.length > 0);
	const isAssessable = $derived(node.assessable && node.ra_id);
	const returnUrl = $derived(page.url.pathname + page.url.search);
	const editHref = $derived(
		node.ra_id ? `/requirement-assessments/${node.ra_id}/edit?next=${encodeURIComponent(returnUrl)}` : ''
	);

	function getResultBadge(result: string | null): { label: string; classes: string } {
		switch (result) {
			case 'compliant':
				return { label: m.compliant(), classes: 'bg-green-100 text-green-800 border-green-200' };
			case 'partially_compliant':
				return {
					label: m.partiallyCompliant(),
					classes: 'bg-yellow-100 text-yellow-800 border-yellow-200'
				};
			case 'non_compliant':
				return {
					label: m.nonCompliant(),
					classes: 'bg-red-100 text-red-800 border-red-200'
				};
			case 'not_applicable':
				return { label: m.notApplicable(), classes: 'bg-gray-100 text-gray-500 border-gray-200' };
			default:
				return {
					label: m.notAssessed(),
					classes: 'bg-gray-50 text-gray-400 border-gray-200'
				};
		}
	}

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
			(ac: Record<string, any>, index: number, self: Record<string, any>[]) =>
				self.findIndex((c: Record<string, any>) => c.id === ac.id) === index
		)
	);
</script>

{#if isAssessable}
	<!-- Leaf row: assessable requirement -->
	<tr class="border-b border-gray-100 hover:bg-gray-50/50 transition-colors">
		<!-- Ref -->
		<td class="px-3 py-2.5 text-sm font-mono text-gray-600 whitespace-nowrap align-top">
			<span style="padding-left: {depth * 1.25}rem">{node.ref_id || ''}</span>
		</td>
		<!-- Requirement Name -->
		<td class="px-3 py-2.5 text-sm text-gray-900 align-top overflow-hidden">
			{#if editHref}
				<Anchor breadcrumbAction="push" href={editHref} class="hover:underline">
					<span class="font-medium">{node.name || ''}</span>
				</Anchor>
			{:else}
				<div class="font-medium">{node.name || ''}</div>
			{/if}
			{#if node.description}
				<div class="text-xs text-gray-500 mt-0.5">{node.description}</div>
			{/if}
		</td>
		<!-- Applicable -->
		<td class="px-3 py-2.5 text-center align-top">
			{#if node.selected === false || node.result === 'not_applicable'}
				<span
					class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700 border border-red-200"
				>
					{m.no()}
				</span>
			{:else}
				<span
					class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 border border-green-200"
				>
					{m.yes()}
				</span>
			{/if}
		</td>
		<!-- Result -->
		<td class="px-3 py-2.5 text-center align-top">
			{#if true}
				{@const badge = getResultBadge(node.result)}
				<span
					class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border {badge.classes}"
				>
					{badge.label}
				</span>
			{/if}
		</td>
		<!-- Observation -->
		<td class="px-3 py-2.5 text-sm text-gray-600 align-top overflow-hidden">
			{#if (node.selected === false || node.result === 'not_applicable') && !node.observation}
				<span class="inline-flex items-center gap-1 text-xs text-amber-600">
					<i class="fas fa-exclamation-triangle text-[10px]"></i>
					{m.observationMissing()}
				</span>
			{:else}
				<span class="break-words">{node.observation || ''}</span>
			{/if}
		</td>
		<!-- Implementation -->
		<td class="px-3 py-2.5 align-top">
			{#if uniqueAppliedControls.length > 0}
				<div class="flex flex-col gap-1.5">
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
				<span class="text-xs text-gray-400">--</span>
			{/if}
		</td>
	</tr>
{:else if hasChildren}
	<!-- Section header: non-assessable node with children -->
	<tr class="bg-gray-50/80 border-b border-gray-200">
		<td
			colspan={6}
			class="px-3 py-2"
		>
			<button
				onclick={() => (expanded = !expanded)}
				class="flex items-center gap-2 w-full text-left group"
				style="padding-left: {depth * 1.25}rem"
			>
				<i
					class="fas fa-chevron-right text-[10px] text-gray-400 transition-transform duration-200 {expanded
						? 'rotate-90'
						: ''}"
				></i>
				<span class="font-semibold text-sm text-gray-800">
					{#if node.ref_id}
						<span class="text-gray-500 font-mono">{node.ref_id}</span>
					{/if}
					{node.name || ''}
				</span>
			</button>
		</td>
	</tr>
	{#if expanded}
		{#each children as [childId, childNode]}
			<svelte:self nodeId={childId} node={childNode} depth={depth + 1} />
		{/each}
	{/if}
{/if}
