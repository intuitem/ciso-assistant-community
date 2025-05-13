<script lang="ts">
	

	// State to track if the card is flipped
	let isFlipped = $state(false);

	// Function to handle the flip action
	function handleFlip() {
		isFlipped = !isFlipped;
	}

	import { m } from '$paraglide/messages';
	interface Props {
		// Accept entity_assessment.data as a prop
		entity_assessment: {
		provider: string;
		entity_assessment_id: string;
		baseline: string;
		solutions: string;
		completion: number;
		review_progress: number;
		conclusion: string;
		last_update: string;
		due_date: string;
		eta_date: string;
		observation: string;
		reviewers: string;
		has_questions: boolean;
	};
	}

	let { entity_assessment }: Props = $props();

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
			warning: 'bg-yellow-100 text-yellow-800',
			ongoing: 'bg-blue-100 text-blue-800',
			completed: 'bg-green-100 text-green-800',
			ok: 'bg-green-100 text-green-800'
		};
		return lookup[conclusion.toLowerCase()] || 'bg-gray-100 text-gray-800';
	}
</script>

<div class="perspective-1000 w-full h-full min-h-[420px]">
	<div
		class="relative w-full h-full transition-transform duration-800 {isFlipped
			? 'rotate-x-180'
			: ''}"
		style="transform-style: preserve-3d;"
	>
		<!-- Front face of the card -->
		<div
			class="absolute w-full h-full rounded-lg shadow-lg bg-white overflow-hidden"
			style="backface-visibility: hidden;"
		>
			<!-- Flip button for front face -->
			<button
				class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center rounded opacity-40 transition-all duration-200 hover:bg-black/5 hover:opacity-100 z-10"
				onclick={handleFlip}
				aria-label="Flip card"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-linecap="round"
					stroke-linejoin="round"
					width="18"
					height="18"
					stroke-width="2"
					class="text-gray-500"
				>
					<path d="M3 8l4 -4l4 4"></path>
					<path d="M7 4l0 9"></path>
					<path d="M13 16l4 4l4 -4"></path>
					<path d="M17 10l0 10"></path>
				</svg>
			</button>

			<!-- Card content (front) -->
			<div class="p-4 h-full flex flex-col">
				<!-- Card header with provider name and conclusion -->
				<div class="flex justify-between items-center pb-3 border-b border-gray-200 mb-3">
					<h3 class="font-bold text-lg text-gray-900">{entity_assessment.provider}</h3>
					<span
						class="px-2 py-1 rounded-full text-xs font-medium mr-10 {getConclusionColor(
							entity_assessment.conclusion
						)}"
					>
						<a href="/entity-assessments/{entity_assessment.entity_assessment_id}"
							>{entity_assessment.conclusion}</a
						>
					</span>
				</div>

				<!-- Card body -->
				<div class="flex flex-col gap-3">
					<!-- Solution name -->
					<div class="mb-3">
						<span class="block text-sm text-gray-500">Solution(s)</span>
						<div class="font-semibold text-gray-800">{entity_assessment.solutions}</div>
					</div>

					<!-- Framework/Baseline -->
					<div class="mb-3">
						<span class="block text-sm text-gray-500">Baseline</span>
						<div
							class="inline-block bg-gray-100 px-2 py-1 rounded text-sm font-mono overflow-hidden"
						>
							<div class="line-clamp-2 min-h-[2.4em] flex items-center">
								{entity_assessment.baseline}
							</div>
						</div>
					</div>
					<span class="block text-sm text-gray-500 mb-2">Compliance review progress</span>
					<!-- Progress circle - SVG can't be fully replaced with Tailwind -->
					<div
						class="flex flex-col items-center"
						title="Any Compliance status except 'not assessed' counts"
					>
						<div class="text-gray-900">
							<svg viewBox="0 0 100 100" width="80" height="80">
								<!-- Background circle -->
								<circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" stroke-width="8" />

								<!-- Progress circle -->
								<circle
									cx="50"
									cy="50"
									r="45"
									fill="none"
									stroke={entity_assessment.review_progress < 50
										? '#ef4444'
										: entity_assessment.review_progress < 75
											? '#eab308'
											: '#22c55e'}
									stroke-width="8"
									stroke-dasharray="283"
									stroke-dashoffset={283 - (283 * entity_assessment.review_progress) / 100}
									transform="rotate(-90 50 50)"
								/>

								<!-- Percentage text -->
								<text
									x="50"
									y="55"
									text-anchor="middle"
									font-size="20"
									font-weight="bold"
									fill="currentColor"
								>
									<a href="/compliance-assessments/{entity_assessment.compliance_assessment_id}"
										>{entity_assessment.review_progress}%</a
									>
								</text>
							</svg>
						</div>
					</div>

					<!-- Dates -->
					<div class="grid grid-cols-2 gap-2 text-sm text-gray-600">
						<div>
							<span class="block text-gray-500">Last update</span>
							{entity_assessment.last_update}
						</div>
						<div>
							<span class="block text-gray-500">Due date</span>
							{entity_assessment.due_date}
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Back face of the card -->
		<div
			class="absolute w-full h-full rounded-lg shadow-md bg-white overflow-hidden"
			style="backface-visibility: hidden; transform: rotateX(180deg);"
		>
			<!-- Flip button for back face -->
			<button
				class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center rounded opacity-40 transition-all duration-200 hover:bg-black/5 hover:opacity-100 z-10"
				onclick={handleFlip}
				aria-label="Flip card back"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-linecap="round"
					stroke-linejoin="round"
					width="18"
					height="18"
					stroke-width="2"
					class="text-gray-500"
				>
					<path d="M3 8l4 -4l4 4"></path>
					<path d="M7 4l0 9"></path>
					<path d="M13 16l4 4l4 -4"></path>
					<path d="M17 10l0 10"></path>
				</svg>
			</button>

			<!-- Card content (back) -->
			<div class="p-4 h-full flex flex-col">
				<h3 class="font-bold text-lg text-gray-900 mb-3 pr-10">{entity_assessment.provider}</h3>

				<!-- Additional details could go here -->
				<div class="mb-4">
					<div class="">
						{#if entity_assessment?.has_questions}
							<!-- Progress bar -->
							<div class="mt-3 mb-6" title="Any answer of associated questions unless not set">
								<div class="flex justify-between items-center mb-1">
									<span class="text-sm text-gray-500">Questions completion</span>
									<span class="text-sm font-medium">{entity_assessment.completion}%</span>
								</div>
								<div class="w-full bg-gray-200 rounded-full h-2">
									<div
										class="h-2 rounded-full {getProgressColor(entity_assessment.completion)}"
										style="width: {entity_assessment.completion}%"
									></div>
								</div>
							</div>
						{/if}
						<div class="w-full mt-4">
							<div class="flex mb-4">
								<div class="w-3 h-3 rounded-full bg-gray-300 mt-1 mr-3"></div>
								<div class="flex-1">
									<p class="font-semibold mb-1">{entity_assessment.reviewers}</p>
									<p class="text-gray-600">Reviewer(s)</p>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="mt-2">
					<span class="block text-sm text-gray-500 mb-2">Observation</span>
					<p class="text-gray-600 leading-relaxed text-xs">
						{entity_assessment.observation}
					</p>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	/* Some styles can't be implemented with Tailwind alone */
	.perspective-1000 {
		perspective: 1000px;
	}

	.rotate-x-180 {
		transform: rotateX(180deg);
	}

	.duration-800 {
		transition-duration: 800ms;
	}
</style>
