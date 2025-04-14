<!-- routes/connected-diagram/+page.svelte -->
<script>
	import { onMount } from 'svelte';

	// Define your nodes
	let nodes = [
		{ id: 1, text: 'User Input', x: 50, y: 100, width: 150, height: 70 },
		{ id: 2, text: 'Data Processing', x: 300, y: 50, width: 150, height: 70 },
		{ id: 3, text: 'Database', x: 300, y: 200, width: 150, height: 70 },
		{ id: 4, text: 'Output Display', x: 550, y: 100, width: 150, height: 70 }
	];

	// Define your connections
	let links = [
		{ source: 1, target: 2, label: 'sends data' },
		{ source: 2, target: 3, label: 'stores' },
		{ source: 3, target: 2, label: 'retrieves' },
		{ source: 2, target: 4, label: 'updates UI' }
	];

	// Create function to get node by id
	function getNodeById(id) {
		return nodes.find((node) => node.id === id);
	}

	// Function to calculate connection path
	function calculatePath(sourceNode, targetNode) {
		const sourceX = sourceNode.x + sourceNode.width / 2;
		const sourceY = sourceNode.y + sourceNode.height / 2;
		const targetX = targetNode.x + targetNode.width / 2;
		const targetY = targetNode.y + targetNode.height / 2;

		return `M${sourceX},${sourceY} L${targetX},${targetY}`;
	}

	// Function to get mid point of a line
	function getMidPoint(sourceNode, targetNode) {
		const sourceX = sourceNode.x + sourceNode.width / 2;
		const sourceY = sourceNode.y + sourceNode.height / 2;
		const targetX = targetNode.x + targetNode.width / 2;
		const targetY = targetNode.y + targetNode.height / 2;

		return {
			x: (sourceX + targetX) / 2,
			y: (sourceY + targetY) / 2
		};
	}
</script>

<div class="container">
	<h1>Connected Nodes Diagram</h1>

	<div class="diagram">
		<div class="diagram-container">
			<svg width="100%" height="400">
				<!-- Define arrow marker -->
				<defs>
					<marker
						id="arrowhead"
						viewBox="0 0 10 10"
						refX="8"
						refY="5"
						markerWidth="6"
						markerHeight="6"
						orient="auto"
					>
						<path d="M 0 0 L 10 5 L 0 10 z" fill="#666" />
					</marker>
				</defs>

				<!-- Draw links first (so they appear behind nodes) -->
				{#each links as link}
					{@const sourceNode = getNodeById(link.source)}
					{@const targetNode = getNodeById(link.target)}
					{@const midPoint = getMidPoint(sourceNode, targetNode)}

					<!-- Draw line with arrow -->
					<path
						d={calculatePath(sourceNode, targetNode)}
						stroke="#666"
						stroke-width="2"
						fill="none"
						marker-end="url(#arrowhead)"
					/>

					<!-- Label background -->
					<rect
						x={midPoint.x - 40}
						y={midPoint.y - 10}
						width="80"
						height="20"
						fill="white"
						rx="5"
						ry="5"
					/>

					<!-- Label text -->
					<text
						x={midPoint.x}
						y={midPoint.y}
						text-anchor="middle"
						dominant-baseline="middle"
						font-size="12px"
					>
						{link.label}
					</text>
				{/each}

				<!-- Draw nodes -->
				{#each nodes as node}
					<g transform="translate({node.x},{node.y})">
						<!-- Node rectangle -->
						<rect
							width={node.width}
							height={node.height}
							rx="5"
							ry="5"
							fill="#f0f0f0"
							stroke="#333"
							stroke-width="1"
							class="node-rect"
						/>

						<!-- Node text -->
						<text
							x={node.width / 2}
							y={node.height / 2}
							text-anchor="middle"
							dominant-baseline="middle"
						>
							{node.text}
						</text>
					</g>
				{/each}
			</svg>
		</div>
	</div>

	<div class="info">
		<h2>How It Works</h2>
		<p>
			This example shows how to create connected divs with labeled arrows using just SVG in
			SvelteKit, without any external dependencies. The nodes are fully customizable with different
			positions, sizes, and connection labels.
		</p>
	</div>
</div>

<style>
	.container {
		max-width: 800px;
		margin: 0 auto;
		padding: 20px;
	}

	.diagram {
		margin: 30px 0;
	}

	.diagram-container {
		width: 100%;
		border: 1px solid #ddd;
		border-radius: 4px;
		overflow: hidden;
	}

	.info {
		margin-top: 40px;
		border-top: 1px solid #eee;
		padding-top: 20px;
	}

	h1 {
		color: #333;
	}

	h2 {
		color: #555;
	}

	.node-rect {
		cursor: pointer;
	}

	.node-rect:hover {
		fill: #e0e0e0;
	}
</style>
