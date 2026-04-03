<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages.js';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const validation = data.validation;

	// Only show "Next submission" if not already a final report or reclassified
	const canProgress =
		data.data.incident_submission !== 'Final report' &&
		data.data.incident_submission !== 'Reclassified as non-major';
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<a
				href="/dora-incident-reports/{data.data.id}/export/json"
				class="btn preset-filled-primary-500 w-full"
			>
				<i class="fa-solid fa-file-code mr-2"></i>{m.asDoraJson()}
			</a>
			{#if canProgress}
				<a
					href="/dora-incident-reports/new?from={data.data.id}"
					class="btn preset-filled-secondary-500 w-full"
				>
					<i class="fa-solid fa-arrow-right mr-2"></i>{m.nextSubmission()}
				</a>
			{/if}
		</div>
	{/snippet}
	{#snippet widgets()}
		<div class="card shadow-lg bg-white p-4 space-y-2">
			<h2 class="text-lg font-bold mb-2">
				<i class="fa-solid fa-circle-check mr-2"></i>{m.doraSchemaValidation()}
			</h2>
			{#if validation.valid}
				<div class="flex items-center space-x-2 text-green-700 bg-green-50 p-3 rounded-md">
					<i class="fa-solid fa-check-circle text-lg"></i>
					<span class="font-medium">{m.schemaValid()}</span>
				</div>
			{:else}
				<div class="bg-amber-50 p-3 rounded-md space-y-2">
					<div class="flex items-center space-x-2 text-amber-700">
						<i class="fa-solid fa-triangle-exclamation text-lg"></i>
						<span class="font-medium">{m.schemaInvalid()}</span>
					</div>
					{#if validation.errors && validation.errors.length > 0}
						<ul class="list-disc list-inside text-sm text-amber-800 space-y-1 ml-2">
							{#each validation.errors.slice(0, 10) as error}
								<li class="font-mono text-xs">{error}</li>
							{/each}
							{#if validation.errors.length > 10}
								<li class="italic">... and {validation.errors.length - 10} more</li>
							{/if}
						</ul>
					{/if}
				</div>
			{/if}
		</div>
	{/snippet}
</DetailView>
