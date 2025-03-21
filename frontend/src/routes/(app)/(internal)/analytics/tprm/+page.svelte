<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';

	// Sample data with added date fields
	const data = [
		{
			name: 'Provider 1',
			framework: 'xyz',
			solution: 'abc',
			progress: 85,
			conclusion: 'blocker',
			lastUpdate: '2025-03-01',
			dueDate: '2025-04-15'
		},
		{
			name: 'Provider 2',
			framework: 'xyz',
			solution: 'abc',
			progress: 62,
			conclusion: 'on track',
			lastUpdate: '2025-02-28',
			dueDate: '2025-05-10'
		},
		{
			name: 'Provider 3',
			framework: 'xyz',
			solution: 'abc',
			progress: 45,
			conclusion: 'delayed',
			lastUpdate: '2025-03-15',
			dueDate: '2025-04-30'
		},
		{
			name: 'Provider 4',
			framework: 'xyz',
			solution: 'abc',
			progress: 93,
			conclusion: 'completed',
			lastUpdate: '2025-03-10',
			dueDate: '2025-03-31'
		},
		{
			name: 'Provider 5',
			framework: 'xyz',
			solution: 'abc',
			progress: 85,
			conclusion: 'blocker',
			lastUpdate: '2025-03-05',
			dueDate: '2025-04-20'
		},
		{
			name: 'Provider 6',
			framework: 'xyz',
			solution: 'abc',
			progress: 70,
			conclusion: 'on track',
			lastUpdate: '2025-03-12',
			dueDate: '2025-05-01'
		},
		{
			name: 'Provider 7',
			framework: 'xyz',
			solution: 'abc',
			progress: 35,
			conclusion: 'delayed',
			lastUpdate: '2025-03-08',
			dueDate: '2025-04-10'
		},
		{
			name: 'Provider 8',
			framework: 'xyz',
			solution: 'abc',
			progress: 88,
			conclusion: 'completed',
			lastUpdate: '2025-03-18',
			dueDate: '2025-03-25'
		}
	];

	// Function to determine progress bar color based on completion percentage
	function getProgressColor(progress: number): string {
		if (progress < 50) return 'bg-red-500';
		if (progress < 75) return 'bg-yellow-500';
		return 'bg-green-500';
	}

	// Function to determine conclusion badge color
	function getConclusionColor(conclusion: string): string {
		const lookup: Record<string, string> = {
			blocker: 'bg-red-100 text-red-800',
			delayed: 'bg-yellow-100 text-yellow-800',
			'on track': 'bg-blue-100 text-blue-800',
			completed: 'bg-green-100 text-green-800'
		};
		return lookup[conclusion.toLowerCase()] || 'bg-gray-100 text-gray-800';
	}
</script>

<div class="card bg-white bg-stripes-pink">
	<div class="p-6 bg-white bg-opacity-95">
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
			{#each data as provider}
				<div
					class="bg-white border border-gray-200 rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300"
				>
					<!-- Card header with provider name and conclusion -->
					<div class="flex justify-between items-center p-4 border-b border-gray-100">
						<h3 class="font-bold text-lg text-gray-900">{provider.name}</h3>
						<span
							class="px-2 py-1 rounded-full text-xs font-medium {getConclusionColor(
								provider.conclusion
							)}"
						>
							{provider.conclusion}
						</span>
					</div>

					<!-- Card body -->
					<div class="p-4">
						<!-- Solution name -->
						<div class="mb-3">
							<span class="text-sm text-gray-500">Solution</span>
							<div class="font-semibold text-gray-800">{provider.solution}</div>
						</div>

						<!-- Framework -->
						<div class="mb-3">
							<span class="text-sm text-gray-500">Baseline</span>
							<div class="inline-block bg-gray-100 px-2 py-1 rounded text-sm font-mono">
								{provider.framework}
							</div>
						</div>

						<!-- Progress bar -->
						<div class="mb-3">
							<div class="flex justify-between items-center mb-1">
								<span class="text-sm text-gray-500">Completion</span>
								<span class="text-sm font-medium">{provider.progress}%</span>
							</div>
							<div class="w-full bg-gray-200 rounded-full h-2">
								<div
									class="h-2 rounded-full {getProgressColor(provider.progress)}"
									style="width: {provider.progress}%"
								></div>
							</div>
						</div>

						<!-- Dates -->
						<div class="grid grid-cols-2 gap-2 text-sm text-gray-600">
							<div>
								<span class="block text-gray-500">Last update</span>
								{provider.lastUpdate}
							</div>
							<div>
								<span class="block text-gray-500">Due date</span>
								{provider.dueDate}
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
</div>

<style>
	.bg-stripes-pink {
		background-image: linear-gradient(
			135deg,
			#07275e 10%,
			transparent 0,
			transparent 50%,
			#07275e 0,
			#07275e 60%,
			transparent 0,
			transparent
		);
		background-size: 7.07px 7.07px;
	}

	.transition-shadow {
		transition: box-shadow 0.3s ease;
	}
</style>
