<script lang="ts">
	import { onMount } from 'svelte';

	interface TreatmentControl {
		id: string;
		name: string;
		eta: string; // ISO date string
	}

	interface ScenarioData {
		id: string;
		name: string;
		currentALE: number | null;
		residualALE: number | null;
		treatmentControls?: TreatmentControl[];
	}

	interface Props {
		scenarios: ScenarioData[];
		currency?: string;
		title?: string;
		width?: string;
		height?: string;
		classesContainer?: string;
		autoPlay?: boolean;
		animationSpeed?: number; // milliseconds per frame
	}

	let {
		scenarios,
		currency = '€',
		title = 'ALE Evolution Timeline',
		width = 'w-full',
		height = 'h-96',
		classesContainer = '',
		autoPlay = false,
		animationSpeed = 2000
	}: Props = $props();

	const chart_id = `ale_timeline_race_${Math.random().toString(36).substr(2, 9)}`;
	let chart: any = null;
	let isPlaying = $state(false);
	let currentFrameIndex = $state(0);

	// Format currency values
	const formatCurrency = (value: number) => {
		const absValue = Math.abs(value);
		if (absValue >= 1_000_000_000) {
			return `${(value / 1_000_000_000).toFixed(1)}B ${currency}`;
		} else if (absValue >= 1_000_000) {
			return `${(value / 1_000_000).toFixed(1)}M ${currency}`;
		} else if (absValue >= 1_000) {
			return `${(value / 1_000).toFixed(0)}K ${currency}`;
		} else {
			return `${value.toFixed(0)} ${currency}`;
		}
	};

	// Generate color palette for scenarios
	const generateColors = (count: number) => {
		const colors = [
			'#3b82f6', // blue
			'#ef4444', // red
			'#10b981', // green
			'#f59e0b', // yellow
			'#8b5cf6', // purple
			'#06b6d4', // cyan
			'#f97316', // orange
			'#84cc16', // lime
			'#ec4899', // pink
			'#6366f1' // indigo
		];

		// If we need more colors, generate additional ones
		while (colors.length < count) {
			const hue = (colors.length * 137.508) % 360; // Golden angle approximation
			colors.push(`hsl(${hue}, 70%, 50%)`);
		}

		return colors.slice(0, count);
	};

	// Prepare timeline data with frames for each treatment implementation
	const prepareTimelineData = () => {
		if (!scenarios || scenarios.length === 0) {
			return [];
		}

		// Collect all unique dates and sort them
		const allDates = new Set<string>();
		allDates.add('current'); // Starting frame

		let hasAnyTreatmentControls = false;
		scenarios.forEach((scenario) => {
			if (scenario.treatmentControls && scenario.treatmentControls.length > 0) {
				hasAnyTreatmentControls = true;
				scenario.treatmentControls.forEach((control) => {
					if (control.eta) {
						allDates.add(control.eta);
					}
				});
			}
		});

		const sortedDates = Array.from(allDates).sort((a, b) => {
			if (a === 'current') return -1;
			if (b === 'current') return 1;
			return new Date(a).getTime() - new Date(b).getTime();
		});

		// Add final frame (always show at least current -> residual)
		sortedDates.push('residual');

		// If no treatment controls with ETAs, add a simple intermediate frame
		if (!hasAnyTreatmentControls && sortedDates.length === 2) {
			// Insert an intermediate frame to show progression
			sortedDates.splice(-1, 0, 'intermediate');
		}

		// Generate frames
		const frames: any[] = [];
		const colors = generateColors(scenarios.length);

		sortedDates.forEach((date, frameIndex) => {
			const frameData: any[] = [];

			scenarios.forEach((scenario, scenarioIndex) => {
				let aleValue = scenario.currentALE || 0;
				let status = 'Current Risk';

				if (date === 'residual') {
					// Final frame shows residual ALE
					aleValue = scenario.residualALE || scenario.currentALE || 0;
					status = 'Residual Risk';
				} else if (date === 'intermediate') {
					// Intermediate frame when no treatment controls with ETAs exist
					const currentALE = scenario.currentALE || 0;
					const residualALE = scenario.residualALE || currentALE;
					aleValue = currentALE - (currentALE - residualALE) * 0.5; // 50% reduction
					status = 'Treatments in Progress';
				} else if (date !== 'current') {
					// Check if any treatments have been implemented by this date
					const implementedTreatments =
						scenario.treatmentControls?.filter(
							(control) => control.eta && new Date(control.eta) <= new Date(date)
						) || [];

					if (implementedTreatments.length > 0) {
						// Interpolate between current and residual ALE based on number of implemented treatments
						const totalTreatments = scenario.treatmentControls?.length || 1;
						const implementedRatio = implementedTreatments.length / totalTreatments;
						const currentALE = scenario.currentALE || 0;
						const residualALE = scenario.residualALE || currentALE;
						aleValue = currentALE - (currentALE - residualALE) * implementedRatio;
						status = `${implementedTreatments.length}/${totalTreatments} treatments implemented`;
					}
				}

				frameData.push({
					name: scenario.name,
					value: aleValue,
					status: status,
					scenarioId: scenario.id,
					color: colors[scenarioIndex]
				});
			});

			// Sort by ALE value (descending for bar race effect)
			frameData.sort((a, b) => b.value - a.value);

			frames.push({
				date: date,
				dateDisplay:
					date === 'current'
						? 'Current State'
						: date === 'residual'
							? 'All Treatments Implemented'
							: date === 'intermediate'
								? 'Treatments in Progress'
								: new Date(date).toLocaleDateString(),
				data: frameData
			});
		});

		return frames;
	};

	// Reactive timeline data that updates when scenarios change
	let timelineData = $derived(prepareTimelineData());

	const updateChart = (frameIndex: number) => {
		if (!chart || !timelineData || frameIndex >= timelineData.length) return;

		const frame = timelineData[frameIndex];
		const maxValue = Math.max(...frame.data.map((d: any) => d.value));

		const option = {
			title: {
				text: frame.dateDisplay,
				left: 'center',
				top: 20,
				textStyle: {
					fontSize: 18,
					fontWeight: 'bold'
				}
			},
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow'
				},
				formatter: function (params: any) {
					const data = params[0];
					return `
						<div style="font-weight: bold">${data.data.name}</div>
						<div>ALE: ${formatCurrency(data.data.value)}</div>
						<div style="color: #666; font-size: 12px">${data.data.status}</div>
					`;
				}
			},
			grid: {
				left: 60,
				right: 60,
				bottom: 80,
				top: 80,
				containLabel: true
			},
			xAxis: {
				type: 'value',
				max: maxValue * 1.1,
				axisLabel: {
					formatter: formatCurrency
				},
				splitLine: {
					show: true,
					lineStyle: {
						type: 'dashed',
						color: '#e5e7eb'
					}
				}
			},
			yAxis: {
				type: 'category',
				data: frame.data.map((d: any) => d.name),
				axisLabel: {
					interval: 0
				},
				inverse: true // Highest values at top
			},
			series: [
				{
					type: 'bar',
					data: frame.data.map((d: any) => ({
						value: d.value,
						name: d.name,
						status: d.status,
						itemStyle: {
							color: d.color
						}
					})),
					barWidth: '60%',
					itemStyle: {
						borderRadius: [0, 4, 4, 0]
					},
					label: {
						show: true,
						position: 'right',
						formatter: function (params: any) {
							return formatCurrency(params.value);
						},
						color: '#374151',
						fontSize: 12
					},
					animationDuration: animationSpeed * 0.8,
					animationEasing: 'cubicOut'
				}
			],
			animation: true,
			animationDuration: animationSpeed * 0.8,
			animationEasing: 'cubicOut'
		};

		chart.setOption(option, true);
	};

	const playAnimation = async () => {
		if (!timelineData || timelineData.length === 0) return;

		isPlaying = true;
		currentFrameIndex = 0;

		for (let i = 0; i < timelineData.length; i++) {
			if (!isPlaying) break;

			currentFrameIndex = i;
			updateChart(i);

			if (i < timelineData.length - 1) {
				await new Promise((resolve) => setTimeout(resolve, animationSpeed));
			}
		}

		isPlaying = false;
	};

	const stopAnimation = () => {
		isPlaying = false;
	};

	const goToFrame = (frameIndex: number) => {
		if (frameIndex >= 0 && frameIndex < timelineData.length) {
			stopAnimation();
			currentFrameIndex = frameIndex;
			updateChart(frameIndex);
		}
	};

	onMount(async () => {
		const echarts = await import('echarts');
		chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });

		// Handle window resize
		const handleResize = () => {
			if (chart) {
				chart.resize();
			}
		};

		window.addEventListener('resize', handleResize);

		return () => {
			window.removeEventListener('resize', handleResize);
			if (chart) {
				chart.dispose();
			}
		};
	});

	// Effect to update chart when timeline data changes
	$effect(() => {
		if (chart && timelineData.length > 0) {
			// Show initial frame
			updateChart(0);

			// Auto-play if enabled
			if (autoPlay) {
				setTimeout(() => playAnimation(), 1000);
			}
		}
	});
</script>

<div class="{classesContainer} {width} {height}">
	<div class="bg-white rounded-lg shadow-sm overflow-hidden">
		<!-- Header with title and controls -->
		<div class="px-6 py-4 border-b border-gray-200">
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold text-gray-900">{title}</h3>

				{#if timelineData.length > 0}
					<div class="flex items-center space-x-3">
						<!-- Play/Stop controls -->
						<div class="flex items-center space-x-2">
							{#if !isPlaying}
								<button
									class="btn btn-sm variant-filled-primary"
									on:click={playAnimation}
									title="Play Animation"
								>
									<i class="fa-solid fa-play text-sm"></i>
								</button>
							{:else}
								<button
									class="btn btn-sm variant-filled-error"
									on:click={stopAnimation}
									title="Stop Animation"
								>
									<i class="fa-solid fa-stop text-sm"></i>
								</button>
							{/if}
						</div>

						<!-- Frame navigation -->
						<div class="flex items-center space-x-2">
							<button
								class="btn btn-sm variant-ghost-surface"
								on:click={() => goToFrame(currentFrameIndex - 1)}
								disabled={currentFrameIndex === 0}
								title="Previous Frame"
							>
								<i class="fa-solid fa-step-backward text-sm"></i>
							</button>

							<span class="text-sm text-gray-600 px-2">
								{currentFrameIndex + 1} / {timelineData.length}
							</span>

							<button
								class="btn btn-sm variant-ghost-surface"
								on:click={() => goToFrame(currentFrameIndex + 1)}
								disabled={currentFrameIndex === timelineData.length - 1}
								title="Next Frame"
							>
								<i class="fa-solid fa-step-forward text-sm"></i>
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Chart container -->
		<div class="p-4">
			<div id={chart_id} class="w-full h-full min-h-[400px]"></div>
		</div>

		<!-- Timeline scrubber -->
		{#if timelineData.length > 0}
			<div class="px-6 py-3 border-t border-gray-200 bg-gray-50">
				<div class="w-full">
					<input
						type="range"
						min="0"
						max={timelineData.length - 1}
						bind:value={currentFrameIndex}
						on:input={(e) => goToFrame(parseInt(e.target.value))}
						class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
						style="background: linear-gradient(to right, #3b82f6 0%, #3b82f6 {(currentFrameIndex /
							(timelineData.length - 1)) *
							100}%, #e5e7eb {(currentFrameIndex / (timelineData.length - 1)) *
							100}%, #e5e7eb 100%)"
					/>
					<div class="flex justify-between text-xs text-gray-500 mt-1">
						<span>Current State</span>
						<span>All Treatments</span>
					</div>
				</div>
			</div>
		{/if}

		<!-- Empty state -->
		{#if !scenarios || scenarios.length === 0}
			<div class="p-8 text-center">
				<div class="flex flex-col items-center space-y-3">
					<i class="fa-solid fa-chart-bar text-3xl text-gray-400"></i>
					<h4 class="text-lg font-medium text-gray-600">No Data Available</h4>
					<p class="text-gray-500 max-w-md">
						No scenarios with ALE data found. Please ensure scenarios have simulation data and
						treatment plans with ETA dates.
					</p>
				</div>
			</div>
		{:else if timelineData.length === 0}
			<!-- Debug: Data exists but timeline data is empty -->
			<div class="p-8 text-center bg-yellow-50 border border-yellow-200">
				<div class="flex flex-col items-center space-y-3">
					<i class="fa-solid fa-exclamation-triangle text-3xl text-yellow-600"></i>
					<h4 class="text-lg font-medium text-yellow-700">Chart Data Processing Issue</h4>
					<div class="text-left text-sm text-yellow-700 bg-yellow-100 p-4 rounded max-w-2xl">
						<p><strong>Scenarios received:</strong> {scenarios?.length || 0}</p>
						<p><strong>Timeline data processed:</strong> {timelineData?.length || 0}</p>
						<details class="mt-2">
							<summary class="cursor-pointer font-medium">View scenario data</summary>
							<pre class="mt-2 text-xs overflow-auto">{JSON.stringify(scenarios, null, 2)}</pre>
						</details>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	/* Custom range slider styling */
	input[type='range']::-webkit-slider-thumb {
		appearance: none;
		height: 16px;
		width: 16px;
		border-radius: 50%;
		background: #3b82f6;
		cursor: pointer;
		border: 2px solid white;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	input[type='range']::-moz-range-thumb {
		height: 16px;
		width: 16px;
		border-radius: 50%;
		background: #3b82f6;
		cursor: pointer;
		border: 2px solid white;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}
</style>
