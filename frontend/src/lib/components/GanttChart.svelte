<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	export let items = [];
	export let groups = undefined;
	export let options = {};
	export let height = '400px';
	export let width = '100%';

	let container;
	let timeline;

	onMount(() => {
		if (browser) {
			// Import both the JS and CSS
			import('vis-timeline/standalone/umd/vis-timeline-graph2d.min.js').then((vis) => {
				// Make sure we have a default option for zoomable if not provided
				const finalOptions = {
					...options,
					height: height,
					width: width
				};

				if (container) {
					// Create the timeline with appropriate parameters
					if (groups) {
						timeline = new vis.Timeline(container, items, groups, finalOptions);
					} else {
						timeline = new vis.Timeline(container, items, finalOptions);
					}

					// Set initial range to show full two years
					const start = new Date('2025-01-01');
					const end = new Date('2026-12-31');
					timeline.setWindow(start, end);

					// Add zoom event handler to adapt axis
					timeline.on('rangechange', function (properties) {
						// Calculate difference in milliseconds
						const diff = properties.end - properties.start;
						const days = diff / (1000 * 60 * 60 * 24);

						// Adjust timeAxis scale based on zoom level
						if (days <= 14) {
							// Days for detailed view
							timeline.setOptions({ timeAxis: { scale: 'day', step: 1 } });
						} else if (days <= 60) {
							// Weeks for medium zoom
							timeline.setOptions({ timeAxis: { scale: 'week', step: 1 } });
						} else if (days <= 365) {
							// Months for zoomed out
							timeline.setOptions({ timeAxis: { scale: 'month', step: 1 } });
						} else {
							// Quarters for very zoomed out
							timeline.setOptions({ timeAxis: { scale: 'month', step: 3 } });
						}
					});

					// Force a redraw after initialization
					setTimeout(() => {
						if (timeline) {
							timeline.redraw();
						}
					}, 100);

					return () => {
						if (timeline) {
							timeline.destroy();
						}
					};
				}
			});
		}
	});
</script>

<svelte:head>
	{#if browser}
		<!-- The CSS is critical for proper zooming functionality -->
		<link
			rel="stylesheet"
			href="https://unpkg.com/vis-timeline@7.7.0/dist/vis-timeline-graph2d.min.css"
		/>
	{/if}
</svelte:head>

<div bind:this={container} class="vis-timeline-container" style="height: {height}; width: {width};">
	{#if !browser}
		<div class="ssr-placeholder">Timeline will render on client-side</div>
	{/if}
</div>

<style>
	.vis-timeline-container {
		border: 1px solid #ddd;
		position: relative;
	}

	:global(.vis-timeline) {
		border: none;
	}

	:global(.vis-item) {
		border-color: #2196f3;
		background-color: #2196f3;
		color: white;
	}

	:global(.vis-item.vis-point) {
		background-color: #ff5722;
	}

	.ssr-placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: #666;
		font-style: italic;
	}
</style>
