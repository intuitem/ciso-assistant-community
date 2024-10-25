<script lang="ts">
	export let data;
	const license = data.license;
</script>

<div class="card bg-white p-4 shadow space-y-4">
	<table class="border-separate border-spacing-y-4">
		<tbody
			><tr class="py-6">
				<td class="text-lg font-bold px-6"> Deployment mode </td>
				<td>{license.deployment_mode}</td>
			</tr>

			<tr>
				<td class="text-lg font-bold px-6"> License type </td>
				<td> {license.type} </td>
			</tr>

			<tr>
				<td class="text-lg font-bold px-6"> Used seats </td>
				<td> {license.users_number} out of {license.users_number_limit} </td>
			</tr>

			<tr>
				<td class="text-lg font-bold px-6"> Seats limit </td>
				<td> Disabled </td>
			</tr>

			<tr>
				<td class="text-lg font-bold px-6"> Support </td>
				<td> {license.support} </td>
			</tr>

			<tr class="">
				<td class="text-lg font-bold px-6"> Expiration date </td>
				<td> {license.expiration_date} </td>
			</tr>
		</tbody>
	</table>
</div>
