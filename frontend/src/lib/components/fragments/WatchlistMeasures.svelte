<script lang="ts">
	import { page } from '$app/stores';
	import type { SecurityMeasureSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages';
	import { formatStringToDate } from '$lib/utils/helpers';

	let request_path: string | null;
	$: request_path = $page.route.id;
	// Shoud i handle the scenario where request_path === null ?

	export let measures_to_review: (typeof SecurityMeasureSchema)[];
	const today = new Date().setHours(0, 0, 0, 0); // Is this the correct way of handling this variable usage ? What is the type of measure.eta ?

	function measureState(date: string) {
		let expiryDate = new Date(date).setHours(0, 0, 0, 0);
		if (expiryDate < today) {
			return 'expired';
		} else if (expiryDate > today) {
			return 'upcoming';
		} else {
			return 'today';
		}
	}
	// Is encodeURIComponent a good function that can replace the urlencode Django filter ?
</script>

<div class="overflow-x-auto shadow-md sm:rounded-lg mt-2">
	<table class="w-full text-sm text-left" id="measuresTable">
		<thead class="text-xs text-gray-700 uppercase bg-gray-50">
			<tr>
				<th data-sort="measure" scope="col" class="px-3 py-3"> {m.name()} </th>
				<th data-sort="parent_project" scope="col" class="px-3 py-3"> {m.domain()} </th>
				<th data-sort="status" scope="col" class="px-3 py-3"> {m.status()} </th>
				<th data-sort="expiry_date" scope="col" class="px-3 py-3"> {m.expiryDate()} </th>
			</tr>
		</thead>
		<tbody>
			{#if measures_to_review.length}
				{#each measures_to_review as measure}
					<tr
						class="bg-white border-b text-ellipsis overflow-hidden hover:text-indigo-500 hover:bg-gray-200 cursor-pointer hover:scale-[0.99] duration-500"
						onclick="window.location='{`/security-measures/${measure.id}`}?next={encodeURIComponent(
							request_path
						)}'"
					>
						<th scope="row" class="px-3 py-4 font-medium">
							{measure.name}
						</th>
						<td class="px-3 py-4">
							{measure.folder.str}
						</td>
						<td class="px-3 py-4">
							{measure.status}
						</td>
						<td class="px-3 py-4">
							{#if measureState(measure.expiry_date) === 'expired'}
								<span class="rounded bg-red-500 text-white p-1 text-xs mr-1">{m.expired()}</span>
							{:else if measureState(measure.expiry_date) === 'upcoming'}
								<span class="rounded bg-blue-500 text-white p-1 text-xs mr-1">{m.upcoming()}</span>
							{:else if measureState(measure.expiry_date) === 'today'}
								<span class="rounded bg-yellow-500 text-white p-1 text-xs mr-1">{m.today()}</span>
							{/if}
							{formatStringToDate(measure.expiry_date)}
						</td>
					</tr>
				{/each}
			{:else}
				<tr class="text-black p-4 text-center">
					<td colspan="8" class="py-2">
						<i class="inline fas fa-exclamation-triangle" />
						<p class="inline test-gray-900">{m.noObjectYet({object: m.securityMeasure().toLowerCase(), e: 'e'})}.</p>
					</td>
				</tr>
			{/if}
		</tbody>
	</table>
</div>
