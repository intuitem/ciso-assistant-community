<script lang="ts">
	// State to track if the card is flipped
	let isFlipped = $state(false);

	// Function to handle the flip action
	function handleFlip() {
		isFlipped = !isFlipped;
	}

	interface Props {
		// Accept entity_assessment.data as a prop
		entity_assessment: {
			provider: string;
			entity_assessment_id: string;
			compliance_assessment_id: string;
			review_assignment_id: string | null;
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
		};
	}

	let { entity_assessment }: Props = $props();

	// Each dial links where its number comes from: what the third party filled in is
	// read in the respondent view, the auditor's own progress on the audit itself.
	const auditHref = $derived(
		`/compliance-assessments/${entity_assessment.compliance_assessment_id}`
	);
	const completionHref = $derived(
		entity_assessment.review_assignment_id
			? `/auditee-assessments/${entity_assessment.review_assignment_id}`
			: auditHref
	);

	// Function to determine conclusion badge color
	function getConclusionColor(conclusion: string): string {
		const lookup: Record<string, string> = {
			blocker: 'bg-red-100 text-red-800',
			warning: 'bg-yellow-100 text-yellow-800',
			ongoing: 'bg-blue-100 text-blue-800',
			completed: 'bg-green-100 text-green-800',
			ok: 'bg-green-100 text-green-800'
		};
		return lookup[conclusion.toLowerCase()] || 'bg-surface-100-900 text-surface-950-50';
	}
</script>

{#snippet progressDial(value: number, label: string, testid: string, hint: string, href: string)}
	<div class="flex flex-col items-center" title={hint}>
		<span class="block text-xs text-surface-600-400 mb-1 text-center">{label}</span>
		<div class="text-surface-950-50">
			<svg viewBox="0 0 100 100" width="72" height="72">
				<circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" stroke-width="8" />
				<circle
					cx="50"
					cy="50"
					r="45"
					fill="none"
					stroke={value < 50 ? '#ef4444' : value < 75 ? '#eab308' : '#22c55e'}
					stroke-width="8"
					stroke-dasharray="283"
					stroke-dashoffset={283 - (283 * (value ?? 0)) / 100}
					transform="rotate(-90 50 50)"
				/>
				<text
					x="50"
					y="55"
					text-anchor="middle"
					font-size="20"
					font-weight="bold"
					fill="currentColor"
				>
					<a data-testid={testid} {href}>{value ?? 0}%</a>
				</text>
			</svg>
		</div>
	</div>
{/snippet}

<div
	class="perspective-1000 w-full h-full min-h-[420px] relative w-full h-full transition-transform duration-800 {isFlipped
		? 'rotate-x-180'
		: ''}"
	role="listitem"
	style="transform-style: preserve-3d;"
>
	<!-- Front face of the card -->
	<div
		class="absolute w-full h-full rounded-lg shadow-lg bg-surface-50-950 overflow-hidden"
		style="backface-visibility: hidden;"
	>
		<!-- Flip button for front face -->
		<button
			class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center rounded-sm opacity-40 transition-all duration-200 hover:bg-black/5 hover:opacity-100 z-10"
			onclick={handleFlip}
			aria-label="Flip card"
			data-testid="flip-button-front"
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
				class="text-surface-600-400"
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
			<div class="flex justify-between items-center pb-3 border-b border-surface-200-800 mb-3">
				<h3 class="font-bold text-lg text-surface-950-50" data-testid="provider">
					<a
						href="/entity-assessments/{entity_assessment.entity_assessment_id}"
						class="hover:text-primary-600 hover:underline"
					>
						{entity_assessment.provider}
					</a>
				</h3>
				<span
					data-testid="conclusion-badge"
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
					<span class="block text-sm text-surface-600-400">Solution(s)</span>
					<div class="font-semibold text-surface-950-50" data-testid="solutions">
						{entity_assessment.solutions}
					</div>
				</div>

				<!-- Framework/Baseline -->
				<div class="mb-3">
					<span class="block text-sm text-surface-600-400">Baseline</span>
					<div
						class="inline-block bg-surface-100-900 px-2 py-1 rounded-sm text-sm font-mono overflow-hidden"
					>
						<div class="line-clamp-2 min-h-[2.4em] flex items-center" data-testid="baseline">
							{entity_assessment.baseline}
						</div>
					</div>
				</div>
				<!-- The two halves of the exchange: what the third party has filled in,
				     and what the auditor has reviewed. Showing one alone reads as no
				     progress while the other side is well underway. -->
				<div class="grid grid-cols-2 gap-1">
					{@render progressDial(
						entity_assessment.completion,
						'Completion',
						'completion',
						'How much of the questionnaire the third party has filled in',
						completionHref
					)}
					{@render progressDial(
						entity_assessment.review_progress,
						'Review progress',
						'review_progress',
						"Any Compliance status except 'not assessed' counts",
						auditHref
					)}
				</div>

				<!-- Dates -->
				<div class="grid grid-cols-2 gap-2 text-sm text-surface-600-400">
					<div>
						<span class="block text-surface-600-400" data-testid="last_update">Last update</span>
						{entity_assessment.last_update}
					</div>
					<div>
						<span class="block text-surface-600-400" data-testid="due_date">Due date</span>
						{entity_assessment.due_date}
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Back face of the card -->
	<div
		class="absolute w-full h-full rounded-lg shadow-md bg-surface-50-950 overflow-hidden"
		style="backface-visibility: hidden; transform: rotateX(180deg);"
	>
		<!-- Flip button for back face -->
		<button
			class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center rounded-sm opacity-40 transition-all duration-200 hover:bg-black/5 hover:opacity-100 z-10"
			onclick={handleFlip}
			aria-label="Flip card back"
			data-testid="flip-button-back"
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
				class="text-surface-600-400"
			>
				<path d="M3 8l4 -4l4 4"></path>
				<path d="M7 4l0 9"></path>
				<path d="M13 16l4 4l4 -4"></path>
				<path d="M17 10l0 10"></path>
			</svg>
		</button>

		<!-- Card content (back) -->
		<div class="p-4 h-full flex flex-col">
			<h3 class="font-bold text-lg text-surface-950-50 mb-3 pr-10">
				<a
					href="/entity-assessments/{entity_assessment.entity_assessment_id}"
					class="hover:text-primary-600 hover:underline"
				>
					{entity_assessment.provider}
				</a>
			</h3>

			<!-- Additional details could go here -->
			<div class="mb-4">
				<div class="">
					<div class="w-full mt-4">
						<div class="flex mb-4">
							<div class="w-3 h-3 rounded-full bg-surface-300-700 mt-1 mr-3"></div>
							<div class="flex-1">
								<p class="font-semibold mb-1" data-testid="reviewers">
									{entity_assessment.reviewers}
								</p>
								<p class="text-surface-600-400">Reviewer(s)</p>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="mt-2">
				<span class="block text-sm text-surface-600-400 mb-2">Observation</span>
				<p class="text-surface-600-400 leading-relaxed text-xs" data-testid="observation">
					{entity_assessment.observation}
				</p>
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
