<script lang="ts">
	import { m } from '$paraglide/messages';
	import { childEntries, isExpandable, previewValue } from './expressions';
	import SecretInlineForm from './SecretInlineForm.svelte';

	interface NodeData {
		key: string;
		label: string;
		output: unknown;
	}

	interface Props {
		variables: Record<string, unknown>;
		nodes: NodeData[];
		secretNames: string[];
		onInsert: (expression: string) => void;
		// Present in edit mode only: shows the quick-add affordance on the
		// secrets group header.
		onAddSecret?: (name: string, value: string) => void;
		// First element of the loop node's collection, resolved
		// against the reference run: rendered as an "item" group whose paths
		// insert as {{item.*}}.
		itemPreview?: unknown;
	}

	let { variables, nodes, secretNames, onInsert, onAddSecret, itemPreview }: Props = $props();

	let addingSecret = $state(false);

	let expanded = $state<Record<string, boolean>>({});

	function toggle(path: string) {
		expanded[path] = !expanded[path];
	}

	let copiedPath = $state<string | null>(null);

	async function copyValue(value: unknown, path: string) {
		const text =
			value !== null && typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
		await navigator.clipboard.writeText(text);
		copiedPath = path;
		setTimeout(() => (copiedPath = null), 1200);
	}
</script>

{#snippet rowActions(value: unknown, path: string, withInsert: boolean)}
	{#if withInsert}
		<button
			type="button"
			title={m.insertReference()}
			class="ml-auto text-[9px] text-primary-500 opacity-0 group-hover:opacity-100 shrink-0 px-0.5 cursor-pointer"
			onclick={(e) => {
				e.stopPropagation();
				onInsert('{{' + path + '}}');
			}}
		>
			<i class="fa-solid fa-arrow-right-to-bracket"></i>
		</button>
	{/if}
	<button
		type="button"
		title={m.copyValue()}
		class="{withInsert
			? ''
			: 'ml-auto '}text-[9px] text-surface-500 hover:text-surface-800-200 opacity-0 group-hover:opacity-100 shrink-0 px-0.5 cursor-pointer"
		onclick={(e) => {
			e.stopPropagation();
			copyValue(value, path);
		}}
	>
		<i class="fa-solid {copiedPath === path ? 'fa-check text-success-500' : 'fa-copy'}"></i>
	</button>
{/snippet}

{#snippet tree(entries: [string, unknown][], basePath: string, depth: number)}
	{#each entries as [key, value] (key)}
		{@const path = basePath ? `${basePath}.${key}` : key}
		<div style="padding-left: {depth * 12}px">
			{#if isExpandable(value)}
				<!-- Rows are divs (not buttons): rowActions renders real <button>
				     controls inside, and buttons must not nest. -->
				<div
					role="button"
					tabindex="0"
					class="w-full flex items-center gap-1 py-0.5 text-[11px] hover:bg-surface-100-900 rounded cursor-pointer text-left group"
					title={'{{' + path + '}}'}
					onclick={() => toggle(path)}
					onkeydown={(e) => {
						if ((e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) {
							e.preventDefault();
							toggle(path);
						}
					}}
				>
					<i
						class="fa-solid fa-chevron-{expanded[path]
							? 'down'
							: 'right'} text-[8px] text-surface-400-600 w-3"
					></i>
					<span class="font-mono text-surface-800-200">{key}</span>
					<span class="text-surface-400-600 truncate ml-1">
						{Array.isArray(value) ? `[${value.length}]` : `{…}`}
					</span>
					{@render rowActions(value, path, true)}
				</div>
				{#if expanded[path]}
					{@render tree(childEntries(value), path, depth + 1)}
				{/if}
			{:else}
				<div
					role="button"
					tabindex="0"
					class="w-full flex items-center gap-1 py-0.5 text-[11px] hover:bg-primary-50 dark:hover:bg-primary-950 rounded cursor-pointer text-left group"
					title={'{{' + path + '}}'}
					onclick={() => onInsert('{{' + path + '}}')}
					onkeydown={(e) => {
						if ((e.key === 'Enter' || e.key === ' ') && e.target === e.currentTarget) {
							e.preventDefault();
							onInsert('{{' + path + '}}');
						}
					}}
				>
					<i class="fa-solid fa-circle text-[4px] text-surface-300-700 w-3 text-center"></i>
					<span class="font-mono text-surface-800-200 shrink-0">{key}</span>
					<span class="text-success-600 dark:text-success-400 truncate ml-1">
						{previewValue(value)}
					</span>
					<i
						class="fa-solid fa-arrow-right-to-bracket ml-auto text-[9px] text-primary-500 opacity-0 group-hover:opacity-100 shrink-0"
					></i>
					{@render rowActions(value, path, false)}
				</div>
			{/if}
		</div>
	{/each}
{/snippet}

<div class="space-y-2" data-testid="data-browser">
	{#if itemPreview !== undefined}
		<div>
			<p class="text-[9px] font-semibold uppercase tracking-wide text-surface-500 mb-0.5">
				<i class="fa-solid fa-rotate mr-1"></i>{m.currentItem()}
			</p>
			{#if isExpandable(itemPreview)}
				{@render tree(childEntries(itemPreview), 'item', 0)}
			{:else}
				{@render tree([['item', itemPreview]], '', 0)}
			{/if}
		</div>
	{/if}

	{#if Object.keys(variables).length}
		<div>
			<p class="text-[9px] font-semibold uppercase tracking-wide text-surface-500 mb-0.5">
				<i class="fa-solid fa-cube mr-1"></i>{m.workflowVariables()}
			</p>
			{@render tree(Object.entries(variables), '', 0)}
		</div>
	{/if}

	{#each nodes as nodeData (nodeData.key)}
		<div>
			<p class="text-[9px] font-semibold uppercase tracking-wide text-surface-500 mb-0.5">
				<i class="fa-solid fa-share-nodes mr-1"></i>{nodeData.label}
			</p>
			{@render tree(childEntries(nodeData.output), `nodes.${nodeData.key}`, 0)}
		</div>
	{/each}

	{#if secretNames.length || onAddSecret}
		<div>
			<div
				class="flex items-center text-[9px] font-semibold uppercase tracking-wide text-surface-500 mb-0.5"
			>
				<span><i class="fa-solid fa-lock mr-1"></i>{m.workflowSecrets()}</span>
				{#if onAddSecret}
					<button
						type="button"
						aria-label={m.addSecret()}
						title={m.addSecret()}
						class="ml-auto text-primary-500 hover:text-primary-600 cursor-pointer px-0.5"
						onclick={() => (addingSecret = !addingSecret)}
						data-testid="databrowser-add-secret"
					>
						<i class="fa-solid fa-plus"></i>
					</button>
				{/if}
			</div>
			{#if addingSecret}
				<SecretInlineForm
					onAdd={(name, value) => {
						onAddSecret?.(name, value);
						addingSecret = false;
					}}
					formClass="mb-1"
					submitIcon="fa-check"
					confirmTestId="databrowser-confirm-secret"
				/>
			{/if}
			{#each secretNames as name (name)}
				<button
					type="button"
					class="w-full flex items-center gap-1 py-0.5 text-[11px] hover:bg-primary-50 dark:hover:bg-primary-950 rounded cursor-pointer text-left group"
					onclick={() => onInsert('{{secrets.' + name + '}}')}
				>
					<i class="fa-solid fa-key text-[8px] text-surface-400-600 w-3 text-center"></i>
					<span class="font-mono text-surface-800-200">{name}</span>
					<span class="text-surface-400-600 ml-1">•••</span>
					<i
						class="fa-solid fa-arrow-right-to-bracket ml-auto text-[9px] text-primary-500 opacity-0 group-hover:opacity-100 shrink-0"
					></i>
				</button>
			{/each}
		</div>
	{/if}
</div>
