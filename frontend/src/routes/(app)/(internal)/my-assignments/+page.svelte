<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
</script>

{@debug data}
<div class="grid gap-2 p-4">
	<div>assigned controls</div>
	<table>
		<thead>
			<th>name</th>
		</thead>
		<tbody>
			{#each data.data.controls as ac}
				<tr>
					<td>{ac.name}</td>
				</tr>
			{/each}</tbody
		>
	</table>
	<div>assigned audits</div>
	<table>
		<thead>
			<th>name</th>
		</thead>
		<tbody>
			{#each data.data.audits as ca}
				<tr>
					<td>{ca.name}</td>
				</tr>
			{/each}</tbody
		>
	</table>
	<div>assigned risk assessments</div>
	<table>
		<thead>
			<th>name</th>
		</thead>
		<tbody>
			{#each data.data.risk_assessments as ra}
				<tr>
					<td>{ra.name}</td>
				</tr>
			{/each}</tbody
		>
	</table>
	<div>assigned scenarios</div>
	<table>
		<thead>
			<th>name</th>
		</thead>
		<tbody>
			{#each data.data.risk_scenarios as rs}
				<tr>
					<td>{rs.name}</td>
				</tr>
			{/each}</tbody
		>
	</table>
</div>
