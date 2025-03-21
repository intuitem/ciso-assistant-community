<script lang="ts">
	// Accept provider data as a prop
	export let provider: {
		provider: string;
		baseline: string;
		solutions: string;
		progress: number;
		conclusion: string;
		last_update: string;
		due_date: string;
	};

	// State to track if the card is flipped
	let isFlipped = false;

	// Function to handle the flip action
	function handleFlip() {
		isFlipped = !isFlipped;
	}

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
			delayed: 'bg-yellow-100 text-yellow-800',
			'on track': 'bg-blue-100 text-blue-800',
			completed: 'bg-green-100 text-green-800',
			ok: 'bg-green-100 text-green-800'
		};
		return lookup[conclusion.toLowerCase()] || 'bg-gray-100 text-gray-800';
	}
</script>

<div class="card-container">
	<div class="card {isFlipped ? 'flipped' : ''}">
		<!-- Front face of the card -->
		<div class="card-face front">
			<!-- Flip button for front face -->
			<button class="corner-button" on:click={handleFlip} aria-label="Flip card">
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
				>
					<path d="M3 8l4 -4l4 4"></path>
					<path d="M7 4l0 9"></path>
					<path d="M13 16l4 4l4 -4"></path>
					<path d="M17 10l0 10"></path>
				</svg>
			</button>

			<!-- Card content (front) -->
			<div class="card-content">
				<!-- Card header with provider name and conclusion -->
				<div class="card-header">
					<h3 class="provider-name">{provider.provider}</h3>
					<span class="conclusion-badge {getConclusionColor(provider.conclusion)}">
						{provider.conclusion}
					</span>
				</div>

				<!-- Card body -->
				<div class="card-body">
					<!-- Solution name -->
					<div class="info-section">
						<span class="info-label">Solution(s)</span>
						<div class="info-value">{provider.solutions}</div>
					</div>

					<!-- Framework/Baseline -->
					<div class="info-section">
						<span class="info-label">Baseline</span>
						<div class="baseline-tag">{provider.baseline}</div>
					</div>

					<!-- Progress bar -->
					<div class="info-section">
						<div class="progress-header">
							<span class="info-label">Completion</span>
							<span class="progress-value">{provider.progress}%</span>
						</div>
						<div class="progress-bar-bg">
							<div
								class="progress-bar-fill {getProgressColor(provider.progress)}"
								style="width: {provider.progress}%"
							></div>
						</div>
					</div>

					<!-- Dates -->
					<div class="dates-grid">
						<div class="date-section">
							<span class="info-label">Last update</span>
							<span>{provider.last_update}</span>
						</div>
						<div class="date-section">
							<span class="info-label">Due date</span>
							<span>{provider.due_date}</span>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Back face of the card -->
		<div class="card-face back">
			<!-- Flip button for back face -->
			<button class="corner-button" on:click={handleFlip} aria-label="Flip card back">
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
				>
					<path d="M3 8l4 -4l4 4"></path>
					<path d="M7 4l0 9"></path>
					<path d="M13 16l4 4l4 -4"></path>
					<path d="M17 10l0 10"></path>
				</svg>
			</button>

			<!-- Card content (back) -->
			<div class="card-content">
				<h3 class="provider-name">{provider.provider}</h3>

				<!-- Additional details could go here -->
				<div class="info-section">
					<span class="info-label">Detailed Progress</span>
					<div class="progress-details">
						<div class="progress-circle">
							<svg viewBox="0 0 100 100" width="80" height="80">
								<!-- Background circle -->
								<circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" stroke-width="8" />

								<!-- Progress circle -->
								<circle
									cx="50"
									cy="50"
									r="45"
									fill="none"
									stroke={provider.progress < 50
										? '#ef4444'
										: provider.progress < 75
											? '#eab308'
											: '#22c55e'}
									stroke-width="8"
									stroke-dasharray="283"
									stroke-dashoffset={283 - (283 * provider.progress) / 100}
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
									{provider.progress}%
								</text>
							</svg>
						</div>
						<div class="timeline">
							<div class="timeline-item">
								<div class="timeline-marker"></div>
								<div class="timeline-content">
									<p class="timeline-date">{provider.last_update}</p>
									<p>Last updated</p>
								</div>
							</div>
							<div class="timeline-item">
								<div
									class="timeline-marker {provider.conclusion === 'completed' ? 'completed' : ''}"
								></div>
								<div class="timeline-content">
									<p class="timeline-date">{provider.due_date}</p>
									<p>Expected completion</p>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="info-section">
					<span class="info-label">Status Summary</span>
					<p class="status-text">
						{#if provider.conclusion === 'completed'}
							This provider has completed implementation with a {provider.progress}% success rate.
						{:else if provider.conclusion === 'delayed' || provider.conclusion === 'blocker'}
							Implementation is facing challenges. Currently at {provider.progress}% completion.
						{:else}
							Implementation is on track at {provider.progress}% completion.
						{/if}
					</p>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.card-container {
		perspective: 1000px;
		width: 100%;
		height: 100%;
		min-height: 360px;
	}

	.card {
		position: relative;
		width: 100%;
		height: 100%;
		transform-style: preserve-3d;
		transition: transform 0.8s;
	}

	.card.flipped {
		transform: rotateX(180deg);
	}

	.card-face {
		position: absolute;
		width: 100%;
		height: 100%;
		backface-visibility: hidden;
		border-radius: 0.5rem;
		box-shadow:
			0 4px 6px -1px rgba(0, 0, 0, 0.1),
			0 2px 4px -1px rgba(0, 0, 0, 0.06);
		background-color: white;
		overflow: hidden;
	}

	.front {
		background-color: white;
	}

	.back {
		background-color: white;
		transform: rotateX(180deg);
	}

	.card-content {
		padding: 1rem;
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	/* Corner button for flipping */
	.corner-button {
		position: absolute;
		width: 32px;
		height: 32px;
		background: transparent;
		border: none;
		cursor: pointer;
		z-index: 10;
		top: 8px;
		right: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
		opacity: 0.4;
		border-radius: 4px;
	}

	.corner-button:hover {
		background: rgba(0, 0, 0, 0.08);
		opacity: 1;
	}

	.corner-button svg {
		color: #6b7280;
	}

	/* Front face styling */
	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid #e5e7eb;
		margin-bottom: 0.75rem;
	}

	.provider-name {
		font-weight: 700;
		font-size: 1.125rem;
		color: #111827;
	}

	.conclusion-badge {
		padding: 0.25rem 0.5rem;
		border-radius: 9999px;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.card-body {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.info-section {
		margin-bottom: 0.75rem;
	}

	.info-label {
		display: block;
		font-size: 0.875rem;
		color: #6b7280;
	}

	.info-value {
		font-weight: 600;
		color: #1f2937;
	}

	.baseline-tag {
		display: inline-block;
		background-color: #f3f4f6;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-family: monospace;
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.25rem;
	}

	.progress-value {
		font-size: 0.875rem;
		font-weight: 500;
	}

	.progress-bar-bg {
		width: 100%;
		background-color: #e5e7eb;
		border-radius: 9999px;
		height: 0.5rem;
	}

	.progress-bar-fill {
		height: 0.5rem;
		border-radius: 9999px;
	}

	.dates-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.5rem;
		font-size: 0.875rem;
		color: #4b5563;
	}

	.date-section {
		display: flex;
		flex-direction: column;
	}

	/* Back face styling */
	.progress-details {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		margin-top: 0.5rem;
	}

	.progress-circle {
		color: #111827;
	}

	.timeline {
		width: 100%;
		margin-top: 1rem;
	}

	.timeline-item {
		display: flex;
		margin-bottom: 1rem;
	}

	.timeline-marker {
		width: 0.75rem;
		height: 0.75rem;
		border-radius: 50%;
		background-color: #d1d5db;
		margin-right: 0.75rem;
		margin-top: 0.25rem;
	}

	.timeline-marker.completed {
		background-color: #22c55e;
	}

	.timeline-content {
		flex: 1;
	}

	.timeline-date {
		font-weight: 600;
		margin-bottom: 0.25rem;
	}

	.status-text {
		margin-top: 0.5rem;
		line-height: 1.5;
		color: #4b5563;
	}
</style>
