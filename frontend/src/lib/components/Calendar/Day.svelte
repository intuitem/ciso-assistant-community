<script lang="ts">
	import { fly } from 'svelte/transition';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

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
			class="flex flex-col border border-gray-200 p-2 rounded-md text-sm h-[8rem] max-h-[8rem]"
		>
			<span class="font-bold bg-primary-500 w-fit text-white rounded-full py-0.5 px-1">{day}</span>
			{#if displayInfo(day, month, year)}
				<div class="flex flex-col justify-center h-full space-y-1">
					{#each displayInfo(day, month, year) as eta}
						<span
							class="flex justify-center cursor-pointer unstyled hover:bg-primary-200 text-primary-700 bg-primary-50 px-1 rounded-md"
						>
							<Anchor href={eta[1]}>
								{eta[0]}
							</Anchor>
						</span>
					{/each}
				</div>
			{/if}
		</div>
	{:else if (day < today.getDate() && month == today.getMonth() + 1 && year == today.getFullYear()) || (month < today.getMonth() + 1 && year == today.getFullYear()) || year < today.getFullYear()}
		<div
			in:fly={{ delay: 100, duration: 300 }}
			class="flex flex-col border p-2 bg-gray-300 text-gray-500 rounded-md text-sm h-[8rem] max-h-[8rem]"
		>
			{day}
			{#if displayInfo(day, month, year)}
				<div class="flex flex-col justify-center h-full space-y-1">
					{#each displayInfo(day, month, year) as eta}
						<span
							class="flex justify-center cursor-pointer unstyled hover:bg-primary-200 text-primary-700 bg-primary-50 px-1 rounded-md"
						>
							<Anchor href={eta[1]}>
								{eta[0]}
							</Anchor>
						</span>
					{/each}
				</div>
			{/if}
		</div>
	{:else}
		<div
			in:fly={{ delay: 100, duration: 300 }}
			class="flex flex-col border border-gray-200 p-2 rounded-md bg-white text-sm h-[8rem] max-h-[8rem]"
		>
			{day}
			{#if displayInfo(day, month, year)}
				<div class="flex flex-col justify-center h-full space-y-1">
					{#each displayInfo(day, month, year) as eta}
						<span
							class="flex justify-center cursor-pointer unstyled hover:bg-primary-200 text-primary-700 bg-primary-50 px-1 rounded-md"
						>
							<Anchor href={eta[1]}>
								{eta[0]}
							</Anchor>
						</span>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
{/key}
