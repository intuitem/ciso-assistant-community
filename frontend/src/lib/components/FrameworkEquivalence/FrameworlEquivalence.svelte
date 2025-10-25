<script lang="ts">
	let { coverages } = $props();
	coverages = coverages.response;
</script>

<table class="table caption-bottom table text-xs table-interactive">
	<thead class="table-head">
		<tr>
			<td class="cursor-pointer select-none uppercase bg-white text-gray-700 hover:text-black">
				URN
			</td>
			<td> Partial coverage </td>
			<td> Full coverage </td>
		</tr>
	</thead>
	<tbody class="w-full border-b border-b-surface-100-900 bg-white">
		{#each Object.entries(coverages) as [urn, cov]}
			<tr class="hover:preset-tonal-primary even:bg-surface-50 cursor-pointer">
				<td>
					{urn}
				</td>
				<td>
					{cov[0]}
				</td>
				<td>
					{cov[1]}
				</td>
			</tr>
		{/each}
	</tbody>
</table>
