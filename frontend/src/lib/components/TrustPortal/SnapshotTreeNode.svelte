<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { RESULT_BY_KEY } from '$lib/utils/portalResults';

	let {
		node,
		path,
		depth = 0,
		mode = 'both',
		collapsed,
		onToggle
	}: {
		node: any;
		path: string;
		depth?: number;
		mode?: string;
		collapsed: Set<string>;
		onToggle: (path: string) => void;
	} = $props();

	const hasChildren = $derived((node.children?.length ?? 0) > 0);
	const open = $derived(!collapsed.has(path));
	const meta = $derived(node.result ? RESULT_BY_KEY[node.result] : null);
	// Legacy flat snapshots have no `assessable` key; a childless node is a leaf.
	const assessable = $derived(node.assessable ?? !hasChildren);
</script>

<div
	class="flex items-center gap-2 border-b border-surface-100-900 py-1.5 text-sm"
	style="padding-left: {depth * 1.5}rem"
>
	{#if hasChildren}
		<button
			type="button"
			onclick={() => onToggle(path)}
			class="w-4 shrink-0 text-surface-400 hover:text-surface-700"
			aria-label={open ? m.collapse() : m.expand()}
		>
			<i class="fa-solid {open ? 'fa-chevron-down' : 'fa-chevron-right'} text-xs"></i>
		</button>
	{:else}
		<span class="w-4 shrink-0"></span>
	{/if}
	{#if node.ref_id}
		<span class="shrink-0 font-mono text-xs text-surface-500">{node.ref_id}</span>
	{/if}
	<span
		class="grow {assessable ? 'text-surface-700-300' : 'font-semibold text-surface-800-200'}"
		title={node.description || undefined}>{node.name}</span
	>
	{#if assessable}
		{#if mode !== 'score' && meta}
			<span
				class="shrink-0 rounded-full px-2 py-0.5 text-xs"
				style="background-color: {meta.color}33">{safeTranslate(meta.label)}</span
			>
		{/if}
		{#if mode !== 'result' && node.score != null}
			<span class="shrink-0 text-xs font-semibold text-violet-600">{node.score}</span>
		{/if}
	{/if}
</div>
{#if hasChildren && open}
	{#each node.children as child, i}
		<svelte:self
			node={child}
			path={`${path}.${i}`}
			depth={depth + 1}
			{mode}
			{collapsed}
			{onToggle}
		/>
	{/each}
{/if}
