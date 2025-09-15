<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import type { NodeProps } from '@xyflow/svelte';

	type $$Props = NodeProps;

	export let data: {
		label: string;
		blockType?: string;
		description?: string;
	};

	// Define visual styles based on block type
	const blockStyles: Record<string, { color: string; icon: string; bgClass: string }> = {
		input: { color: '#3b82f6', icon: '📥', bgClass: 'bg-blue-50 border-blue-300' },
		process: { color: '#10b981', icon: '⚙️', bgClass: 'bg-green-50 border-green-300' },
		decision: { color: '#f59e0b', icon: '❓', bgClass: 'bg-yellow-50 border-yellow-300' },
		output: { color: '#8b5cf6', icon: '📤', bgClass: 'bg-purple-50 border-purple-300' },
		risk: { color: '#ef4444', icon: '⚠️', bgClass: 'bg-red-50 border-red-300' },
		control: { color: '#6366f1', icon: '🛡️', bgClass: 'bg-indigo-50 border-indigo-300' },
		compliance: { color: '#14b8a6', icon: '✓', bgClass: 'bg-teal-50 border-teal-300' },
		default: { color: '#6b7280', icon: '📦', bgClass: 'bg-gray-50 border-gray-300' }
	};

	$: style = blockStyles[data.blockType || 'default'] || blockStyles.default;

	// Determine if node should have input/output handles
	$: hasInput = data.blockType !== 'input';
	$: hasOutput = data.blockType !== 'output';
</script>

<!-- Input Handle -->
{#if hasInput}
	<Handle
		type="target"
		position={Position.Left}
		id="target"
		style="background: {style.color}; width: 12px; height: 12px;"
	/>
{/if}

<!-- Node Content -->
<div class="node-content flex items-center space-x-2 p-3 rounded-lg border-2 {style.bgClass} min-w-[150px] relative">
	<span class="text-2xl">{style.icon}</span>
	<div class="flex-1">
		<div class="font-semibold text-sm" style="color: {style.color}">
			{data.label}
		</div>
		{#if data.description}
			<div class="text-xs text-gray-600 mt-1">
				{data.description}
			</div>
		{/if}
	</div>
</div>

<!-- Output Handle -->
{#if hasOutput}
	<Handle
		type="source"
		position={Position.Right}
		id="source"
		style="background: {style.color}; width: 12px; height: 12px;"
	/>
{/if}

<style>
	.node-content {
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		transition: all 0.2s ease;
	}

	.node-content:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}
</style>
