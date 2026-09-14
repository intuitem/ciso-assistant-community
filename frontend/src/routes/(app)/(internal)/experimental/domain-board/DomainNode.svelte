<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext, tick } from 'svelte';

	interface Props {
		id: string;
		data: {
			label: string;
			contentType: string;
			childCount: number;
			descendantCount: number;
			collapsed: boolean;
			movable: boolean;
			isRoot: boolean;
		};
	}

	let { id, data }: Props = $props();

	const board = getContext<{
		drag: { draggingId: string | null; targetId: string | null; blocked: string[] };
		renameDomain: (id: string, name: string) => Promise<boolean>;
		createSubDomain: (parentId: string, parentName: string) => void;
		detachToRoot: (id: string) => void;
		toggleCollapse: (id: string) => void;
	}>('domainBoard');

	// Drag feedback comes from shared board state rather than node data: rewriting
	// the `nodes` array mid-drag would replace the object xyflow is dragging.
	const dragging = $derived(board?.drag.draggingId === id);
	const dropCandidate = $derived(board?.drag.targetId === id);
	const dropBlocked = $derived(
		board?.drag.draggingId != null && !dragging && board.drag.blocked.includes(id)
	);

	const isEnclave = $derived(data.contentType === 'EN');
	const locked = $derived(data.isRoot || isEnclave || !data.movable);

	const accentClass = $derived(
		data.isRoot ? 'bg-secondary-400' : isEnclave ? 'bg-warning-400' : 'bg-primary-400'
	);
	const borderClass = $derived(
		dropCandidate
			? 'border-success-500'
			: data.isRoot
				? 'border-secondary-300'
				: isEnclave
					? 'border-warning-300'
					: 'border-primary-300'
	);

	let hovered = $state(false);
	let editing = $state(false);
	let draftName = $state('');
	let saving = $state(false);
	let inputEl = $state<HTMLInputElement | null>(null);

	async function startEdit(event: MouseEvent) {
		event.stopPropagation();
		if (!data.movable) return;
		draftName = data.label;
		editing = true;
		await tick();
		inputEl?.focus();
		inputEl?.select();
	}

	async function commitEdit() {
		const trimmed = draftName.trim();
		if (!trimmed || trimmed === data.label) {
			editing = false;
			return;
		}
		saving = true;
		let ok = false;
		try {
			ok = (await board?.renameDomain(id, trimmed)) ?? false;
		} finally {
			// Clear the disabled state even if renameDomain throws, or the input
			// would stay locked with no way back.
			saving = false;
		}
		if (ok) editing = false;
	}

	function onInputKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			commitEdit();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			editing = false;
			draftName = '';
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="domain-node relative rounded-base border-[1.5px] bg-surface-50-950 px-3 py-2 shadow-sm select-none transition-opacity {borderClass}"
	class:opacity-30={dropBlocked}
	class:ring-2={dropCandidate}
	class:ring-success-400={dropCandidate}
	class:shadow-lg={dragging}
	style="width: 210px; height: 58px;"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
>
	<div class="absolute left-0 top-0 bottom-0 w-1 rounded-l-base {accentClass}"></div>

	<div class="ml-1 flex h-full flex-col justify-center">
		<div class="flex items-center gap-1.5">
			<span
				class="inline-block rounded border px-1 py-0.5 text-[9px] font-semibold tracking-wide uppercase"
				class:bg-secondary-100={data.isRoot}
				class:text-secondary-700={data.isRoot}
				class:border-secondary-200={data.isRoot}
				class:bg-warning-100={isEnclave}
				class:text-warning-700={isEnclave}
				class:border-warning-200={isEnclave}
				class:bg-primary-100={!data.isRoot && !isEnclave}
				class:text-primary-700={!data.isRoot && !isEnclave}
				class:border-primary-200={!data.isRoot && !isEnclave}
			>
				{data.isRoot ? 'Global' : isEnclave ? 'Enclave' : 'Domain'}
			</span>
			{#if data.childCount > 0}
				<button
					type="button"
					class="nodrag nopan cursor-pointer rounded px-1 font-mono text-[9px] text-surface-500 hover:bg-surface-200-800"
					title={data.collapsed
						? `Expand — ${data.descendantCount} domain(s) hidden below`
						: `Collapse — hides ${data.descendantCount} domain(s)`}
					onclick={(e) => {
						e.stopPropagation();
						board?.toggleCollapse(id);
					}}
					onmousedown={(e) => e.stopPropagation()}
					ondblclick={(e) => e.stopPropagation()}
				>
					<i class="fa-solid {data.collapsed ? 'fa-plus' : 'fa-minus'} text-[8px]"></i>
					{data.descendantCount}
				</button>
			{/if}
			{#if locked && !data.isRoot}
				<i class="fa-solid fa-lock text-[8px] text-surface-400" title="You can't move this domain"
				></i>
			{/if}
		</div>

		{#if editing}
			<input
				bind:this={inputEl}
				bind:value={draftName}
				onkeydown={onInputKeydown}
				onblur={commitEdit}
				onclick={(e) => e.stopPropagation()}
				ondblclick={(e) => e.stopPropagation()}
				onmousedown={(e) => e.stopPropagation()}
				disabled={saving}
				class="nodrag nopan mt-1 w-full rounded border border-primary-400 bg-surface-50-950 px-1 py-0.5 text-[12px] leading-tight font-semibold text-surface-900-100 outline-none"
			/>
		{:else}
			<div
				role="button"
				tabindex="0"
				title={data.movable ? 'Double-click to rename' : data.label}
				class="mt-1 truncate text-[12px] leading-tight font-semibold text-surface-900-100"
				class:cursor-text={data.movable}
				ondblclick={startEdit}
			>
				{data.label}
			</div>
		{/if}
	</div>

	{#if hovered && board?.drag.draggingId === null}
		<div class="nopan nodrag absolute -top-2 -right-2 flex gap-0.5">
			<button
				type="button"
				aria-label="Create sub-domain"
				title="Create a sub-domain here"
				class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full bg-primary-500 text-[8px] text-white shadow hover:bg-primary-600"
				onclick={(e) => {
					e.stopPropagation();
					board?.createSubDomain(id, data.label);
				}}
				onmousedown={(e) => e.stopPropagation()}
			>
				<i class="fa-solid fa-plus text-[8px]"></i>
			</button>
			{#if !locked}
				<button
					type="button"
					aria-label="Move to top level"
					title="Move to top level (directly under Global)"
					class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full bg-surface-200 text-[8px] text-surface-700 shadow hover:bg-surface-300"
					onclick={(e) => {
						e.stopPropagation();
						board?.detachToRoot(id);
					}}
					onmousedown={(e) => e.stopPropagation()}
				>
					<i class="fa-solid fa-arrow-turn-up text-[8px]"></i>
				</button>
			{/if}
			{#if !data.isRoot}
				<a
					href="/folders/{id}"
					target="_blank"
					rel="noopener"
					aria-label="Open domain in new tab"
					title="Open domain in new tab"
					class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full bg-surface-200 text-[8px] text-surface-700 shadow hover:bg-surface-300"
					onclick={(e) => e.stopPropagation()}
					onmousedown={(e) => e.stopPropagation()}
				>
					<i class="fa-solid fa-arrow-up-right-from-square text-[8px]"></i>
				</a>
			{/if}
		</div>
	{/if}

	<Handle
		type="target"
		position={Position.Left}
		class="!h-3 !w-3 !border-2 !border-surface-600 !bg-surface-50-950"
	/>
	<Handle
		type="source"
		position={Position.Right}
		class="!h-3 !w-3 !border-2 !border-surface-600 !bg-surface-50-950"
	/>
</div>
