<script lang="ts">
	import LossExceedanceCurve from '$lib/components/Chart/LossExceedanceCurve.svelte';
	import { pageTitle } from '$lib/utils/stores';

	$pageTitle = 'Loss Exceedance Curve';

	// Realistic Monte Carlo simulation results - Loss Exceedance data
	// Simulates 10,000 scenarios of cybersecurity incident losses
	const generateMonteCarloSampleData = () => {
		// Define 25 samples organized as powers of 10
		const percentiles = [
			{ loss: 1, exceedance: 0.6 }, // 60% chance of exceeding $100 (10^2)
			{ loss: 10, exceedance: 0.595 }, // 60% chance of exceeding $100 (10^2)
			{ loss: 100, exceedance: 0.59 }, // 60% chance of exceeding $100 (10^2)
			{ loss: 200, exceedance: 0.58 }, // 58% chance of exceeding $200
			{ loss: 500, exceedance: 0.55 }, // 55% chance of exceeding $500
			{ loss: 1000, exceedance: 0.52 }, // 52% chance of exceeding $1K (10^3)
			{ loss: 2000, exceedance: 0.49 }, // 49% chance of exceeding $2K
			{ loss: 5000, exceedance: 0.45 }, // 45% chance of exceeding $5K
			{ loss: 10000, exceedance: 0.42 }, // 42% chance of exceeding $10K (10^4)
			{ loss: 20000, exceedance: 0.38 }, // 38% chance of exceeding $20K
			{ loss: 50000, exceedance: 0.34 }, // 34% chance of exceeding $50K
			{ loss: 100000, exceedance: 0.3 }, // 30% chance of exceeding $100K (10^5)
			{ loss: 200000, exceedance: 0.26 }, // 26% chance of exceeding $200K
			{ loss: 500000, exceedance: 0.22 }, // 22% chance of exceeding $500K
			{ loss: 1000000, exceedance: 0.18 }, // 18% chance of exceeding $1M (10^6)
			{ loss: 2000000, exceedance: 0.15 }, // 15% chance of exceeding $2M
			{ loss: 5000000, exceedance: 0.12 }, // 12% chance of exceeding $5M
			{ loss: 10000000, exceedance: 0.09 }, // 9% chance of exceeding $10M (10^7)
			{ loss: 20000000, exceedance: 0.07 }, // 7% chance of exceeding $20M
			{ loss: 50000000, exceedance: 0.05 }, // 5% chance of exceeding $50M
			{ loss: 100000000, exceedance: 0.035 }, // 3.5% chance of exceeding $100M (10^8)
			{ loss: 200000000, exceedance: 0.025 }, // 2.5% chance of exceeding $200M
			{ loss: 500000000, exceedance: 0.018 }, // 1.8% chance of exceeding $500M
			{ loss: 1000000000, exceedance: 0.012 } // 1.2% chance of exceeding $1B (10^9)
		];

		return percentiles.map((p) => [p.loss, p.exceedance]);
	};

	const sampleData = generateMonteCarloSampleData();
</script>

<div class="space-y-8 p-6">
	<div class="text-center">
		<h1 class="text-3xl font-bold text-gray-900 mb-2">Loss Exceedance Curve Analysis</h1>
		<p class="text-gray-600 max-w-3xl mx-auto">
			Loss Exceedance Curves show the probability that losses will exceed a given amount. These
			curves are essential for risk quantification and help organizations understand their potential
			financial exposure to various risk scenarios.
		</p>
	</div>

	<div class="bg-white rounded-lg shadow-lg p-6">
		<h2 class="text-xl font-semibold mb-4 text-center">
			Chart Comparison: Full vs Light Rendering
		</h2>

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
			<!-- Full featured chart -->
			<div class="space-y-2">
				<h3 class="font-medium text-center">Full Rendering (Log X, Linear Y, Grids On)</h3>
				<LossExceedanceCurve
					data={sampleData}
					name="full-chart"
					title="Full Feature Chart"
					enableTooltip={true}
					xAxisScale="log"
					yAxisScale="linear"
					showXGrid={true}
					showYGrid={true}
					minorSplitLine={true}
					autoXMax={true}
				/>
			</div>

			<!-- Light chart -->
			<div class="space-y-2">
				<h3 class="font-medium text-center">Light Rendering (No Grids, No Tooltip, No Labels)</h3>
				<LossExceedanceCurve
					data={sampleData}
					name="light-chart"
					title="Light Version"
					enableTooltip={false}
					xAxisScale="log"
					yAxisScale="linear"
					showXGrid={false}
					showYGrid={false}
					xAxisLabel=""
					yAxisLabel=""
					autoYMax={true}
					xMax={100_000}
				/>
			</div>
		</div>

		<!-- Additional examples -->
		<div class="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
			<!-- Linear X scale -->
			<div class="space-y-2">
				<h3 class="font-medium text-center">Linear X-Axis Scale</h3>
				<LossExceedanceCurve
					data={sampleData}
					name="linear-x-chart"
					title="Linear X Scale"
					enableTooltip={true}
					xAxisScale="linear"
					yAxisScale="linear"
					showXGrid={true}
					showYGrid={true}
					autoXMax={true}
				/>
			</div>
		</div>
	</div>
</div>
