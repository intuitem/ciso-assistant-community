<script lang="ts">
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages';
	import type { User } from '$lib/utils/types';
	import { formatStringToDate } from '$lib/utils/helpers';
	import { languageTag } from '$paraglide/runtime';

	let request_path: string | null;
	$: request_path = $page.route.id;
	// Shoud i handle the scenario where request_path === null ?

	export let user: User;
	export let acceptances_to_review: any[]; // Change this type later on

	let today = new Date().setHours(0, 0, 0, 0);

	function acceptanceState(date: string) {
		let eta = new Date(date).setHours(0, 0, 0, 0);
		if (eta < today) {
			return 'expired';
		} else if (eta > today) {
			return 'upcoming';
		} else {
			return 'today';
		}
	}
</script>

<div class="overflow-x-auto shadow-md sm:rounded-lg mt-2">
	<table class="w-full text-sm text-left" id="acceptancesTable">
		<thead class="text-xs text-gray-700 uppercase bg-gray-50">
			<tr>
				<th data-sort="acceptance" scope="col" class="px-3 py-3"> {m.name()} </th>
				<th data-sort="parent_project" scope="col" class="px-3 py-3"> {m.domain()} </th>
				<th data-sort="status" scope="col" class="px-3 py-3"> {m.approver()} </th>
				<th data-sort="eta" scope="col" class="px-3 py-3"> {m.expiryDate()} </th>
			</tr>
		</thead>
		<tbody>
			{#if acceptances_to_review.length}
				{#each acceptances_to_review as acceptance}
					<tr
						class="bg-white border-b text-ellipsis overflow-hidden hover:text-indigo-500 hover:bg-gray-200 cursor-pointer hover:scale-[0.99] duration-500"
						onclick="window.location='{`/risk-acceptances/${acceptance.id}`}?next={encodeURIComponent(
							request_path
						)}'"
					>
						<th scope="row" class="px-3 py-4 font-medium">
							{#if acceptance.approver == user.id && acceptance.state == 'submitted'}
								<span class="mr-1 p-1 rounded-md text-xs bg-indigo-500 text-white">
									{m.actionRequested()}
								</span>
							{/if}
							{acceptance.name}
						</th>
						<th class="px-3 py-4">
							{acceptance.folder.str}
						</th>
						<th class="px-3 py-4">
							{acceptance.approver.str}
						</th>
						<th class="px-3 py-4">
							{#if acceptanceState(acceptance.expiry_date) === 'expired'}
								<span class="rounded bg-red-500 text-white p-1 text-xs mr-1">{m.expired()}</span>
							{:else if acceptanceState(acceptance.expiry_date) === 'upcoming'}
								<span class="rounded bg-blue-500 text-white p-1 text-xs mr-1">{m.upcoming()}</span>
							{:else if acceptanceState(acceptance.expiry_date) === 'today'}
								<span class="rounded bg-yellow-500 text-white p-1 text-xs mr-1">{m.today()}</span>
							{/if}
							{formatStringToDate(acceptance.expiry_date,languageTag())}
						</th>
					</tr>
				{/each}
			{:else}
				<tr class="text-black p-4 text-center">
					<td colspan="8" class="py-2">
						<i class="inline fas fa-exclamation-triangle" />
						<p class="inline test-gray-900">
							{m.noRiskAcceptanceYet()}.
						</p>
					</td>
				</tr>
			{/if}
		</tbody>
	</table>
</div>
