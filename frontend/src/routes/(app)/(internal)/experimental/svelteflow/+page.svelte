<script lang="ts">
	import { SvelteFlow, Controls, Background, MiniMap } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import type { Node, Edge, NodeTypes } from '@xyflow/svelte';
	import CustomNode from './CustomNode.svelte';

	// Block library - different types of nodes
	const blockLibrary = [
		{ type: 'input', label: 'Input', color: 'bg-blue-500' },
		{ type: 'process', label: 'Process', color: 'bg-green-500' },
		{ type: 'decision', label: 'Decision', color: 'bg-yellow-500' },
		{ type: 'output', label: 'Output', color: 'bg-purple-500' },
		{ type: 'risk', label: 'Risk Assessment', color: 'bg-red-500' },
		{ type: 'control', label: 'Security Control', color: 'bg-indigo-500' },
		{ type: 'compliance', label: 'Compliance Check', color: 'bg-teal-500' }
	];

	// Custom node types
	const nodeTypes: NodeTypes = {
		custom: CustomNode
	};

	// Reactive arrays for nodes and edges
	let nodes: Node[] = [
		{
			id: '1',
			type: 'custom',
			data: { label: 'Start Process', blockType: 'input', description: 'Beginning of workflow' },
			position: { x: 250, y: 50 }
		}
	];

	let edges: Edge[] = [];

	let nodeId = 2;
	let selectedNode: Node | null = null;

	// Drag and drop functionality
	let draggedBlockType: string | null = null;

	function onDragStart(event: DragEvent, blockType: string) {
		if (event.dataTransfer) {
			event.dataTransfer.setData('application/svelteflow', blockType);
			event.dataTransfer.effectAllowed = 'move';
		}
		draggedBlockType = blockType;
	}

	function onDrop(event: DragEvent) {
		event.preventDefault();

		const type = event.dataTransfer?.getData('application/svelteflow');

		if (type && draggedBlockType) {
			// Get the SvelteFlow container for proper positioning
			const flowElement = event.currentTarget as HTMLElement;
			const flowBounds = flowElement.getBoundingClientRect();

			const position = {
				x: event.clientX - flowBounds.left - 75,
				y: event.clientY - flowBounds.top - 25
			};

			const blockInfo = blockLibrary.find(b => b.type === type);
			const newNode: Node = {
				id: nodeId.toString(),
				type: 'custom',
				position,
				data: {
					label: blockInfo?.label || 'New Node',
					blockType: type,
					description: `${blockInfo?.label} component`
				}
			};

			nodes = [...nodes, newNode];
			nodeId++;
		}

		draggedBlockType = null;
	}

	function onDragOver(event: DragEvent) {
		event.preventDefault();
		event.dataTransfer!.dropEffect = 'move';
	}

	function onNodesChange(event: CustomEvent) {
		const changes = event.detail;
		// Apply changes to nodes (position updates, deletions, etc.)
		nodes = nodes.map(node => {
			const change = changes.find(c => c.id === node.id);
			if (change) {
				if (change.type === 'position' && change.position) {
					return { ...node, position: change.position };
				}
				if (change.type === 'remove') {
					return null;
				}
			}
			return node;
		}).filter(Boolean) as Node[];
	}

	function onEdgesChange(event: CustomEvent) {
		const changes = event.detail;
		// Apply changes to edges more carefully to prevent flickering
		edges = edges.map(edge => {
			const change = changes.find(c => c.id === edge.id);
			if (change) {
				if (change.type === 'remove') {
					return null;
				}
				// Handle other edge changes like selection, etc.
				return { ...edge, ...change };
			}
			return edge;
		}).filter(Boolean) as Edge[];
	}

	function onConnect(event: CustomEvent) {
		const connection = event.detail;

		// Check if connection has required properties
		if (!connection || !connection.source || !connection.target) {
			return;
		}

		// Ensure proper handle targeting - source should connect to target handle
		const sourceHandle = connection.sourceHandle || 'source';
		const targetHandle = connection.targetHandle || 'target';

		// Prevent duplicate edges
		const edgeId = `e${connection.source}-${connection.target}`;
		const existingEdge = edges.find(edge => edge.id === edgeId);

		if (!existingEdge && connection.source !== connection.target) {
			edges = [...edges, {
				id: edgeId,
				source: connection.source,
				target: connection.target,
				sourceHandle,
				targetHandle,
				type: 'smoothstep',
				animated: false
			}];
		}
	}

	function clearCanvas() {
		nodes = [];
		edges = [];
		nodeId = 1;
		selectedNode = null;
	}

	function exportFlow() {
		const flowData = {
			nodes,
			edges
		};
		console.log('Flow Data:', JSON.stringify(flowData, null, 2));
		alert('Flow data exported to console');
	}

	function onNodeClick(event: CustomEvent) {
		const nodeId = event.detail.node.id;
		selectedNode = nodes.find(n => n.id === nodeId) || null;
	}

	function updateSelectedNode(field: string, value: string) {
		if (!selectedNode) return;

		nodes = nodes.map(node =>
			node.id === selectedNode!.id
				? { ...node, data: { ...node.data, [field]: value } }
				: node
		);

		// Update selectedNode to reflect changes
		selectedNode = { ...selectedNode, data: { ...selectedNode.data, [field]: value } };
	}

	function onConnectStart(event: CustomEvent) {
		// Called when connection starts - can be used to prevent unwanted connections
		// Clear any selected node to avoid interference
		selectedNode = null;
	}

	function onConnectEnd(event: CustomEvent) {
		// Called when connection ends - cleanup any temporary states
		// This helps prevent the flickering issue
	}
</script>

<div class="flex h-screen">
	<!-- Block Library Sidebar -->
	<div class="w-64 bg-gray-100 border-r border-gray-300 p-4 overflow-y-auto">
		<h2 class="text-lg font-semibold mb-4">Block Library</h2>
		<div class="space-y-2">
			{#each blockLibrary as block}
				<div
					class="p-3 rounded cursor-move border border-gray-300 hover:border-gray-400 transition-colors {block.color} text-white font-medium"
					draggable="true"
					ondragstart={(e) => onDragStart(e, block.type)}
				>
					{block.label}
				</div>
			{/each}
		</div>

		<!-- Controls -->
		<div class="mt-6 space-y-2">
			<button
				class="w-full px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
				onclick={clearCanvas}
			>
				Clear Canvas
			</button>
			<button
				class="w-full px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
				onclick={exportFlow}
			>
				Export Flow
			</button>
		</div>

		<!-- Instructions -->
		<div class="mt-6 text-sm text-gray-600">
			<h3 class="font-semibold mb-2">Instructions:</h3>
			<ul class="space-y-1">
				<li>" Drag blocks from library to canvas</li>
				<li>" Connect nodes by dragging from one to another</li>
				<li>" Move nodes by dragging them</li>
				<li>" Delete nodes/edges by selecting and pressing Delete</li>
			</ul>
		</div>
	</div>

	<!-- SvelteFlow Canvas -->
	<div class="flex-1 relative">
		<div class="absolute inset-0">
			<SvelteFlow
				{nodes}
				{edges}
				{nodeTypes}
				onnodeschange={onNodesChange}
				onedgeschange={onEdgesChange}
				onconnect={onConnect}
				onconnectstart={onConnectStart}
				onconnectend={onConnectEnd}
				onnodeclick={onNodeClick}
				ondrop={onDrop}
				ondragover={onDragOver}
				fitView
				snapToGrid={true}
				snapGrid={[15, 15]}
				connectionMode="loose"
				deleteKeyCode="Delete"
				multiSelectionKeyCode="Meta"
				defaultEdgeOptions={{ type: 'smoothstep' }}
			>
				<Controls />
				<MiniMap />
				<Background variant="dots" gap={12} size={1} />
			</SvelteFlow>
		</div>
	</div>

	<!-- Properties Panel -->
	<div class="w-80 bg-gray-50 border-l border-gray-300 p-4 overflow-y-auto">
		<h2 class="text-lg font-semibold mb-4">Properties</h2>

		{#if selectedNode}
			<div class="space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Node ID</label>
					<input
						type="text"
						value={selectedNode.id}
						disabled
						class="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-600"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Label</label>
					<input
						type="text"
						value={selectedNode.data.label || ''}
						oninput={(e) => updateSelectedNode('label', e.target?.value || '')}
						class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
					<textarea
						value={selectedNode.data.description || ''}
						oninput={(e) => updateSelectedNode('description', e.target?.value || '')}
						rows="3"
						class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					></textarea>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Block Type</label>
					<select
						value={selectedNode.data.blockType || 'default'}
						onchange={(e) => updateSelectedNode('blockType', e.target?.value || 'default')}
						class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
					>
						{#each blockLibrary as block}
							<option value={block.type}>{block.label}</option>
						{/each}
					</select>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 mb-1">Position</label>
					<div class="grid grid-cols-2 gap-2">
						<div>
							<label class="block text-xs text-gray-500 mb-1">X</label>
							<input
								type="number"
								value={Math.round(selectedNode.position.x)}
								disabled
								class="w-full px-2 py-1 border border-gray-300 rounded text-sm bg-gray-100 text-gray-600"
							/>
						</div>
						<div>
							<label class="block text-xs text-gray-500 mb-1">Y</label>
							<input
								type="number"
								value={Math.round(selectedNode.position.y)}
								disabled
								class="w-full px-2 py-1 border border-gray-300 rounded text-sm bg-gray-100 text-gray-600"
							/>
						</div>
					</div>
				</div>

				<button
					class="w-full px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
					onclick={() => {
						nodes = nodes.filter(node => node.id !== selectedNode?.id);
						selectedNode = null;
					}}
				>
					Delete Node
				</button>
			</div>
		{:else}
			<p class="text-gray-500 text-sm">Click on a node to edit its properties</p>
		{/if}

		<!-- Flow Statistics -->
		<div class="mt-8 pt-4 border-t border-gray-300">
			<h3 class="text-sm font-semibold mb-2">Flow Statistics</h3>
			<div class="space-y-1 text-sm text-gray-600">
				<div>Nodes: {nodes.length}</div>
				<div>Connections: {edges.length}</div>
			</div>
		</div>
	</div>
</div>

<style>
	:global(.svelte-flow__node) {
		border: 2px solid #1a192b;
		border-radius: 8px;
		padding: 10px;
		background: white;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	:global(.svelte-flow__node.selected) {
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
	}

	:global(.svelte-flow__edge) {
		stroke: #374151;
		stroke-width: 2px;
		fill: none;
	}

	:global(.svelte-flow__edge.selected) {
		stroke: #3b82f6;
		stroke-width: 3px;
	}

	:global(.svelte-flow__edge-path) {
		stroke: #374151;
		stroke-width: 2px;
		fill: none;
	}

	:global(.svelte-flow__connection-line) {
		stroke: #3b82f6;
		stroke-width: 2px;
		stroke-dasharray: 5, 5;
		fill: none;
	}

	:global(.svelte-flow__handle) {
		border: 2px solid white;
		border-radius: 50%;
		width: 12px !important;
		height: 12px !important;
	}

	:global(.svelte-flow__handle-left) {
		left: -6px !important;
	}

	:global(.svelte-flow__handle-right) {
		right: -6px !important;
	}
</style>
