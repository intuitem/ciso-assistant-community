<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { getContext, tick } from 'svelte';

	interface Props {
		id: string;
		data: {
			label: string;
			childCount: number;
			descendantCount: number;
			collapsed: boolean;
			contentCount: number;
			subtreeContentCount: number;
			deletable: boolean;
			stagedForDelete: boolean;
			movable: boolean;
			canReceive: boolean;
			isRoot: boolean;
			staged: boolean;
			orientation: 'horizontal' | 'vertical';
		};
	}

	let { id, data }: Props = $props();

	const board = getContext<{
		drag: { draggingId: string | null; targetId: string | null; blocked: string[] };
		renameDomain: (id: string, name: string) => Promise<boolean>;
		createSubDomain: (parentId: string, parentName: string) => void;
		detachToRoot: (id: string) => void;
		toggleCollapse: (id: string) => void;
		stageDelete: (id: string) => void;
		unstageDelete: (id: string) => void;
	}>('domainBoard');

	// From shared board state, not node data: rewriting `nodes` mid-drag would replace
	// the object xyflow is dragging.
	const dragging = $derived(board?.drag.draggingId === id);
	const dropCandidate = $derived(board?.drag.targetId === id);
	const dropBlocked = $derived(
		board?.drag.draggingId != null && !dragging && board.drag.blocked.includes(id)
	);

	const locked = $derived(data.isRoot || !data.movable);

	// On the axis the layout runs along, so edges leave a parent on its children's side.
	const horizontal = $derived(data.orientation === 'horizontal');
	const targetSide = $derived(horizontal ? Position.Left : Position.Top);
	const sourceSide = $derived(horizontal ? Position.Right : Position.Bottom);

	const accentClass = $derived(data.isRoot ? 'bg-secondary-400' : 'bg-primary-400');
	const borderClass = $derived(
		data.stagedForDelete
			? 'border-error-500'
			: dropCandidate
				? 'border-success-500'
				: data.staged
					? 'border-warning-500'
					: data.isRoot
						? 'border-secondary-300'
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
			saving = false; // even if renameDomain throws, or the input stays locked
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
	class:cursor-grab={!locked}
	class:active:cursor-grabbing={!locked}
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
				class:bg-secondary-50-950={data.isRoot}
				class:text-secondary-700-300={data.isRoot}
				class:border-secondary-200-800={data.isRoot}
				class:bg-primary-50-950={!data.isRoot}
				class:text-primary-700-300={!data.isRoot}
				class:border-primary-200-800={!data.isRoot}
			>
				{data.isRoot ? 'Global' : 'Domain'}
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
			{#if data.subtreeContentCount > 0}
				<span
					class="font-mono text-[9px] text-surface-500"
					title={data.contentCount === data.subtreeContentCount
						? `${data.contentCount} object(s) in this domain`
						: `${data.contentCount} here, ${data.subtreeContentCount} including sub-domains`}
				>
					<i class="fa-solid fa-box-archive text-[8px]"></i>
					{data.subtreeContentCount}
				</span>
			{/if}
			{#if data.stagedForDelete}
				<i
					class="fa-solid fa-trash text-[8px] text-error-600"
					title="Staged for deletion — not applied yet"
				></i>
			{/if}
			{#if data.staged}
				<i
					class="fa-solid fa-arrow-right-arrow-left text-[8px] text-warning-600-400"
					title="Staged move — not saved yet"
				></i>
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
			{#if data.canReceive}
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
			{/if}
			{#if !locked}
				<button
					type="button"
					aria-label="Move to top level"
					title="Move to top level (directly under Global)"
					class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full bg-surface-200-800 text-[8px] text-surface-700-300 shadow hover:bg-surface-300-700"
					onclick={(e) => {
						e.stopPropagation();
						board?.detachToRoot(id);
					}}
					onmousedown={(e) => e.stopPropagation()}
				>
					<i class="fa-solid fa-arrow-turn-up text-[8px]"></i>
				</button>
			{/if}
			{#if data.stagedForDelete}
				<button
					type="button"
					aria-label="Keep this domain"
					title="Cancel the staged deletion"
					class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full bg-surface-200-800 text-[8px] text-surface-700-300 shadow hover:bg-surface-300-700"
					onclick={(e) => {
						e.stopPropagation();
						board?.unstageDelete(id);
					}}
					onmousedown={(e) => e.stopPropagation()}
				>
					<i class="fa-solid fa-rotate-left text-[8px]"></i>
				</button>
			{:else if data.deletable}
				<button
					type="button"
					aria-label="Delete this domain"
					title="Stage this empty domain for deletion"
					class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full bg-error-500 text-[8px] text-white shadow hover:bg-error-600"
					onclick={(e) => {
						e.stopPropagation();
						board?.stageDelete(id);
					}}
					onmousedown={(e) => e.stopPropagation()}
				>
					<i class="fa-solid fa-trash text-[8px]"></i>
				</button>
			{/if}
			{#if !data.isRoot}
				<a
					href="/folders/{id}"
					target="_blank"
					rel="noopener"
					aria-label="Open domain in new tab"
					title="Open domain in new tab"
					class="flex h-4 w-4 cursor-pointer items-center justify-center rounded-full bg-surface-200-800 text-[8px] text-surface-700-300 shadow hover:bg-surface-300-700"
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
		position={targetSide}
		class="!h-3 !w-3 !border-2 !border-surface-600 !bg-surface-50-950"
	/>
	<Handle
		type="source"
		position={sourceSide}
		class="!h-3 !w-3 !border-2 !border-surface-600 !bg-surface-50-950"
	/>
</div>
