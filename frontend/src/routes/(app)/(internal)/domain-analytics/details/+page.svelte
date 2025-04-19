<script lang="ts">
	import Card from '$lib/components/DataViz/Card.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';
	export let data: PageData;
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
</script>

<main class="bg-white">
	<div class="grid grid-cols-4 p-2 gap-2">
		{#await data.stream.metrics}
			<div class="col-span-3 lg:col-span-1">
				<div>Refreshing data ..</div>
				<LoadingSpinner />
			</div>
		{:then metrics}
			<fieldset
				class="fieldset col-span-full bg-slate-50 border-slate-300 border rounded-lg grid grid-cols-6 gap-2 p-2"
			>
				<legend class="m-2 text-lg font-bold capitalize"
					><i class="fa-solid fa-shield-halved m-2"></i>{m.appliedControls()}</legend
				>
				<Card count={metrics.controls.total} label={m.sumpageTotal()} />
				<div class="col-span-full"></div>
				<Card count={metrics.controls.active} label={m.sumpageActive()} />
				<Card count={metrics.controls.deprecated} label={m.sumpageDeprecated()} />
				<div class="col-span-full"></div>
				<Card count={metrics.controls.to_do} label={m.sumpageToDo()} />
				<Card count={metrics.controls.in_progress} label={m.sumpageInProgress()} />
				<Card count={metrics.controls.on_hold} label={m.sumpageOnHold()} />
				<div class="col-span-full"></div>
				<Card count={metrics.controls.p1} label={m.sumpageP1()} />
				<Card count={metrics.controls.eta_missed} label={m.sumpageEtaMissed()} />
			</fieldset>
		{:catch error}
			<div class="col-span-3 lg:col-span-1">
				<p class="text-red-500">Error loading metrics</p>
			</div>
		{/await}
		<div class="border col-span-full panel">compliance</div>
		<div class="border col-span-full">risk</div>
	</div>
</main>
