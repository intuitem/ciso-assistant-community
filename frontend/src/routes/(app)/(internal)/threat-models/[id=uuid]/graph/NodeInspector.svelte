<script lang="ts">
	import { m } from '$paraglide/messages';
	import ObjectPicker from './ObjectPicker.svelte';

	interface Props {
		node: any | null;
		readonly?: boolean;
		onUpdate: (patch: Record<string, unknown>) => void;
		onDelete: (id: string) => void;
	}

	let { node, readonly = false, onUpdate, onDelete }: Props = $props();

	const data = $derived(node?.data ?? {});
	const isOperator = $derived(data.kind === 'operator');
</script>

<aside class="w-80 shrink-0 overflow-y-auto border-l border-surface-200-800 bg-surface-50-950 p-3">
	{#if !node}
		<p class="text-xs text-surface-500 italic">{m.threatModelSelectNodeHint()}</p>
	{:else}
		<div class="mb-3 flex items-start justify-between gap-2">
			<div class="min-w-0">
				{#if data.refId}
					<p class="font-mono text-[10px] text-surface-500">{data.refId}</p>
				{/if}
				<p class="text-sm font-semibold text-wrap">
					{data.label || (isOperator ? data.operator : m.threatModelCustomNode())}
				</p>
				{#if data.parentName}
					<p class="text-[10px] text-surface-600-400 text-wrap">{data.parentName}</p>
				{/if}
			</div>
			{#if !readonly}
				<button
					type="button"
					class="btn btn-sm preset-tonal-error shrink-0"
					onclick={() => onDelete(node.id)}
				>
					<i class="fa-solid fa-trash text-xs"></i>
				</button>
			{/if}
		</div>

		{#if isOperator}
			<div class="space-y-1">
				<span class="text-xs font-semibold text-surface-700-300">{m.logicOperator()}</span>
				<div class="flex gap-2">
					{#each ['AND', 'OR'] as op (op)}
						<button
							type="button"
							class="btn btn-sm grow {data.operator === op
								? 'preset-filled-secondary-500'
								: 'preset-tonal-surface'}"
							disabled={readonly}
							onclick={() => onUpdate({ operator: op })}
						>
							{op}
						</button>
					{/each}
				</div>
				<p class="text-[10px] text-surface-500">{m.threatModelOperatorHint()}</p>
			</div>
		{:else}
			<div class="space-y-3">
				<label class="space-y-1 block">
					<span class="text-xs font-semibold text-surface-700-300">{m.label()}</span>
					<input
						type="text"
						class="input w-full px-2 py-1 text-xs"
						disabled={readonly}
						value={data.customLabel ?? ''}
						placeholder={data.name ?? ''}
						oninput={(e) => onUpdate({ customLabel: e.currentTarget.value })}
					/>
				</label>

				<label class="space-y-1 block">
					<span class="text-xs font-semibold text-surface-700-300">{m.description()}</span>
					<textarea
						class="textarea w-full px-2 py-1 text-xs"
						rows="3"
						disabled={readonly}
						value={data.description ?? ''}
						oninput={(e) => onUpdate({ description: e.currentTarget.value })}
					></textarea>
				</label>

				<label class="flex items-center gap-2 text-xs">
					<input
						type="checkbox"
						class="checkbox"
						disabled={readonly}
						checked={Boolean(data.isHighlighted)}
						onchange={(e) => onUpdate({ isHighlighted: e.currentTarget.checked })}
					/>
					<span class="font-semibold text-surface-700-300">{m.threatModelHighlightNode()}</span>
				</label>

				<ObjectPicker
					label={m.assets()}
					endpoint="assets"
					disabled={readonly}
					value={data.assets ?? []}
					onChange={(ids) => onUpdate({ assets: ids })}
				/>
				<ObjectPicker
					label={m.appliedControls()}
					endpoint="applied-controls"
					disabled={readonly}
					value={data.appliedControls ?? []}
					onChange={(ids) => onUpdate({ appliedControls: ids })}
				/>
				<ObjectPicker
					label={m.vulnerabilities()}
					endpoint="vulnerabilities"
					disabled={readonly}
					value={data.vulnerabilities ?? []}
					onChange={(ids) => onUpdate({ vulnerabilities: ids })}
				/>
			</div>
		{/if}
	{/if}
</aside>
