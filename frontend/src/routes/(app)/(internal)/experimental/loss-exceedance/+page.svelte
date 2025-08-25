<script lang="ts">
	import LossExceedanceCurve from '$lib/components/Chart/LossExceedanceCurve.svelte';
	import { pageTitle } from '$lib/utils/stores';

	$pageTitle = 'Loss Exceedance Curve';

	// Sample data representing standard risk scenario - spans multiple orders of magnitude
	const sampleData = [
		[100, 0.5],
		[1000, 0.4],
		[10000, 0.25],
		[100000, 0.15],
		[500000, 0.1],
		[1000000, 0.08],
		[5000000, 0.05],
		[10000000, 0.03],
		[50000000, 0.02],
		[100000000, 0.01],
		[500000000, 0.005],
		[1000000000, 0.002],
		[10000000000, 0.001]
	];
</script>

<div class="space-y-8 p-6">
	<div class="text-center">
		<h1 class="text-3xl font-bold text-gray-900 mb-2">Loss Exceedance Curve Analysis</h1>
		<p class="text-gray-600 max-w-3xl mx-auto">
			Loss Exceedance Curves show the probability that losses will exceed a given amount.
			These curves are essential for risk quantification and help organizations understand
			their potential financial exposure to various risk scenarios.
		</p>
	</div>

	<div class="bg-white rounded-lg shadow-lg p-6">
		<h2 class="text-xl font-semibold mb-4 text-center">Standard Risk Profile</h2>
		<div class="flex justify-center">
			<LossExceedanceCurve
				data={sampleData}
				name="standard-curve"
				title="Standard Risk Profile"
			/>
		</div>
		<div class="mt-4 text-sm text-gray-600 max-w-2xl mx-auto">
			<p><strong>Key insights:</strong></p>
			<ul class="list-disc list-inside mt-2 space-y-1">
				<li>50% chance of losses exceeding $100</li>
				<li>40% chance of losses exceeding $1K</li>
				<li>15% chance of losses exceeding $100K</li>
				<li>5% chance of losses exceeding $5M</li>
				<li>0.2% chance of losses exceeding $1B</li>
			</ul>
		</div>
	</div>

	<div class="bg-blue-50 rounded-lg p-6">
		<h3 class="text-lg font-semibold mb-3 text-blue-900">Understanding Loss Exceedance Curves</h3>
		<div class="text-sm text-blue-800 space-y-2">
			<p><strong>What they show:</strong> The probability that actual losses will exceed a given amount over a specific time period (typically one year).</p>
			<p><strong>How to read them:</strong> The x-axis shows potential loss amounts, while the y-axis shows the probability of exceeding that loss.</p>
			<p><strong>Risk management use:</strong> These curves help in setting insurance coverage levels, determining risk appetite, and making informed decisions about risk mitigation investments.</p>
			<p><strong>Key metrics:</strong></p>
			<ul class="list-disc list-inside ml-4 mt-1 space-y-1">
				<li><strong>Value at Risk (VaR):</strong> Loss amount at a specific confidence level</li>
				<li><strong>Tail Value at Risk (TVaR):</strong> Expected loss given that VaR is exceeded</li>
				<li><strong>Maximum Probable Loss (MPL):</strong> Worst-case scenario within reasonable probability</li>
			</ul>
		</div>
	</div>
</div>
