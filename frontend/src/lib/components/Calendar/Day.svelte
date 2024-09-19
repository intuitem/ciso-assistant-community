<script lang="ts">
	import { fly } from 'svelte/transition';

	export let day: number;
	export let month: number;
	export let year: number;
	export let info: any[];

	let today = new Date();

	function displayInfo(day: number, month: number, year: number) {
		let res: (typeof info)[] = [];
		for (let i = 0; i < info.length; i++) {
			if (
				info[i].date.getDate() == day &&
				info[i].date.getMonth() + 1 == month &&
				info[i].date.getFullYear() == year
			) {
				res = res.concat([[info[i].label, info[i].link]]);
			}
		}
		return res;
	}
</script>

{#key month}
	{#if day == today.getDate() && month == today.getMonth() + 1 && year == today.getFullYear()}
		<div
			in:fly={{ delay: 100, duration: 300 }}
			class="flex flex-col border border-gray-200 p-2 bg-indigo-500 text-white rounded-lg text-sm"
		>
			{day}
			{#if displayInfo(day, month, year)}
				<div class="flex flex-col justify-center h-full">
					{#each displayInfo(day, month, year) as eta}
						<li class="unstyled hover:underline">
							<a href={eta[1]}>
								{eta[0]}
							</a>
						</li>
					{/each}
				</div>
			{/if}
		</div>
	{:else if (day < today.getDate() && month == today.getMonth() + 1  && year == today.getFullYear() ) || (month < today.getMonth() + 1 && year == today.getFullYear()) || year < today.getFullYear()}
		<div
			in:fly={{ delay: 100, duration: 300 }}
			class="flex flex-col border p-2 bg-gray-300 text-gray-500 rounded-lg text-sm"
		>
			{day}
			{#if displayInfo(day, month, year)}
				<div class="flex flex-col justify-center h-full">
					{#each displayInfo(day, month, year) as eta}
						<li class="unstyled hover:underline text-red-500">
							<a href={eta[1]}>
								{eta[0]}
							</a>
						</li>
					{/each}
				</div>
			{/if}
		</div>
	{:else}
		<div
			in:fly={{ delay: 100, duration: 300 }}
			class="flex flex-col border border-gray-200 p-2 rounded-lg bg-white text-sm"
		>
			{day}
			{#if displayInfo(day, month, year)}
				<div class="flex flex-col justify-center h-full">
					{#each displayInfo(day, month, year) as eta}
						<li class="unstyled hover:underline text-primary-500">
							<a href={eta[1]}>
								{eta[0]}
							</a>
						</li>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
{/key}
