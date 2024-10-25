<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	import type { PopupSettings } from '@skeletonlabs/skeleton';
	import { popup } from '@skeletonlabs/skeleton';

	function stopPropagation(event: Event): void {
		event.stopPropagation();
	}

	const popupDownload: PopupSettings = {
		event: 'click',
		target: 'popupDownload',
		placement: 'bottom'
	};
</script>

{#if data.table}
	<div class="shadow-lg">
		<ModelTable source={data.table} URLModel={data.URLModel}>
			<span slot="actions" let:meta class="space-x-2 whitespace-nowrap">
				<a
					href="/risk-assessments/{meta.id}/remediation-plan"
					class="unstyled cursor-pointer text-xl text-slate-500 hover:text-indigo-700"
					on:click={stopPropagation}><i class="fa-solid fa-heart-pulse" /></a
				>
				<button
					class="unstyled cursor-pointer text-xl text-slate-500 hover:text-indigo-700"
					use:popup={popupDownload}
					on:click={stopPropagation}><i class="fa-solid fa-download" /></button
				>
				<div
					class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1"
					data-popup="popupDownload"
				>
					<p class="block px-4 py-2 text-sm text-gray-800">Risk risk_assessment</p>
					<a
						href="/risk-assessments/{meta.id}/export/pdf"
						class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
						on:click={stopPropagation}>... as PDF</a
					>
					<a
						href="/risk-assessments/{meta.id}/export/csv"
						class="block px-4 py-2 text-sm text-gray-800 border-b hover:bg-gray-200"
						on:click={stopPropagation}>... as csv</a
					>
					<p class="block px-4 py-2 text-sm text-gray-800">Treatment plan</p>
					<a
						href="/risk-assessments/{meta.id}/remediation-plan/export/pdf"
						class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
						on:click={stopPropagation}>... as PDF</a
					>
					<a
						href="/risk-assessments/{meta.id}/remediation-plan/export/csv"
						class="block px-4 py-2 text-sm text-gray-800 border-b hover:bg-gray-200"
						on:click={stopPropagation}>... as csv</a
					>
				</div>
			</span>
		</ModelTable>
	</div>
{/if}
