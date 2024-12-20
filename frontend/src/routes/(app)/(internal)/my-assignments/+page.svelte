<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { languageTag } from '$paraglide/runtime';
	import * as m from '$paraglide/messages';
	import AuditCard from './AuditCard.svelte';
	import ActivityTracker from './ActivityTracker.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	const eta_span_class = { true: 'bg-orange-400 text-white' };
	const status_span_class = {
		on_hold: 'bg-violet-500 text-white p-1 rounded',
		deprecated: 'bg-red-400 text-white p-1 rounded'
	};
</script>

<div class=" grid grid-cols-12 p-6 gap-6">
	<div
		class="col-span-full text-lg font-black underline underline-offset-4 decoration-4 decoration-pink-500"
	>
		{m.controls()}
	</div>
	<div class="text-left col-span-full lg:col-span-8">
		<div class="relative overflow-x-auto shadow-lg rounded-lg">
			<table class="w-full text-sm text-left rtl:text-right text-gray-500 dark:text-gray-400">
				<thead
					class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400"
				>
					<tr>
						<th scope="col" class="px-6 py-3"> {m.name()} </th>
						<th scope="col" class="px-6 py-3"> {m.csfFunction()} </th>
						<th scope="col" class="px-6 py-3"> {m.status()} </th>
						<th scope="col" class="px-6 py-3"> {m.eta()} </th>
						<th scope="col" class="px-6 py-3"> {m.folder()} </th>
					</tr>
				</thead>
				<tbody>
					{#each data.data.controls as ac}
						<tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
							<th
								scope="row"
								class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white"
							>
								<Anchor href="/applied-controls/{ac.id}" class="hover:text-violet-400"
									>{ac.name}</Anchor
								>
							</th>
							<td class="px-6 py-4"> {ac.csf_function ?? '-'} </td>
							<td class="px-6 py-4"
								><span class={status_span_class[ac.status]}>{safeTranslate(ac.status) ?? '-'}</span>
							</td>
							<td class="px-6 py-4">
								<span class=" p-1 rounded {eta_span_class[ac.eta_missed]}">
									{formatDateOrDateTime(ac.eta, languageTag()) ?? '-'}
								</span>
							</td>
							<td class="px-6 py-4">{ac.folder.str} </td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>

	<div class=" border-red-50 col-span-full lg:col-span-4 flex justify-center items-center">
		<ActivityTracker metrics={data.data.metrics} />
	</div>

	<div
		class="col-span-full text-lg font-black underline underline-offset-4 decoration-4 decoration-green-300"
	>
		Audits
	</div>

	<div class="col-span-full grid grid-cols-2 lg:grid-cols-3 gap-4">
		{#each data.data.audits as ca}
			<AuditCard audit={ca} />
		{/each}
	</div>

	<div class="text-left col-span-full lg:col-span-6">
		<div class="text-lg font-black underline underline-offset-4 decoration-4 decoration-orange-300">
			{m.riskAssessments()}
		</div>
		<div class="text-left">
			<div class="relative overflow-x-auto shadow-lg rounded-lg">
				<table class="w-full text-sm text-left rtl:text-right text-gray-500 dark:text-gray-400">
					<thead
						class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400"
					>
						<tr>
							<th scope="col" class="px-6 py-3"> {m.name()} </th>
							<th scope="col" class="px-6 py-3"> {m.status()} </th>
							<th scope="col" class="px-6 py-3"> ETA </th>
						</tr>
					</thead>
					<tbody>
						{#each data.data.risk_assessments as ra}
							<tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
								<th
									scope="row"
									class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white"
								>
									<Anchor href="/risk-assessments/{ra.id}" class="hover:text-violet-400"
										>{ra.name}</Anchor
									>
								</th>
								<td class="px-6 py-4"> {safeTranslate(ra.status) ?? '-'} </td>
								<td class="px-6 py-4"> {formatDateOrDateTime(ra.eta, languageTag()) ?? '-'} </td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</div>

	<div class="text-left col-span-full lg:col-span-6">
		<div class="text-lg font-black underline underline-offset-4 decoration-4 decoration-purple-300">
			{m.assignedRisks()}
		</div>
		<div class="text-left">
			<div class="relative overflow-x-auto shadow-lg rounded-lg">
				<table class="w-full text-sm text-left rtl:text-right text-gray-500 dark:text-gray-400">
					<thead
						class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400"
					>
						<tr>
							<th scope="col" class="px-6 py-3"> {m.name()} </th>
							<th scope="col" class="px-6 py-3"> {m.status()} </th>
							<th scope="col" class="px-6 py-3"> {m.currentLevel()} </th>
							<th scope="col" class="px-6 py-3"> {m.residualLevel()} </th>
						</tr>
					</thead>
					<tbody>
						{#each data.data.risk_scenarios as rs}
							<tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
								<th
									scope="row"
									class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white"
								>
									<Anchor href="/risk-scenarios/{rs.id}" class="hover:text-violet-400"
										>{rs.name}</Anchor
									>
								</th>
								<td class="px-6 py-4"> {safeTranslate(rs.treatment) ?? '-'} </td>
								<td class="px-6 py-4"> {safeTranslate(rs.current_level.name) ?? '-'}</td>
								<td class="px-6 py-4"> {safeTranslate(rs.residual_level.name) ?? '-'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</div>
</div>
