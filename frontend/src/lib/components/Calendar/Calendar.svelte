<script lang="ts">
	import { fly } from 'svelte/transition';
	import Day from './Day.svelte';
	import { SlideToggle } from '@skeletonlabs/skeleton';
	import { page } from '$app/stores';
	import { showAllTasks } from '$lib/utils/stores';

	import { m } from '$paraglide/messages';

	export let info: object[];

	const today = new Date();
	export let month = today.getMonth() + 1;
	export let year = today.getFullYear();
	$: daysInMonth = new Date(year, month, 0).getDate();
	$: firstDay = new Date(year, month - 1, 1).getDay();

	const daysOfWeek = [
		m.monday(),
		m.tuesday(),
		m.wednesday(),
		m.thursday(),
		m.friday(),
		m.saturday(),
		m.sunday()
	];
	const monthNames = [
		m.january(),
		m.february(),
		m.march(),
		m.april(),
		m.may(),
		m.june(),
		m.july(),
		m.august(),
		m.september(),
		m.october(),
		m.november(),
		m.december()
	];

	function currentMonth() {
		return `/calendar/${today.getFullYear()}/${today.getMonth() + 1}`;
	}

	function nextMonth(year: number, month: number) {
		if (month == 12) {
			return `/calendar/${year + 1}/1`;
		} else {
			return `/calendar/${year}/${month + 1}`;
		}
	}

	function prevMonth(year: number, month: number) {
		if (month == 1) {
			return `/calendar/${year - 1}/12`;
		} else {
			return `/calendar/${year}/${month - 1}`;
		}
	}

	const user = $page.data.user;
	let filteredInfo = info;

	$: {
		if (!$showAllTasks) {
			filteredInfo = info.filter((event) => event.users.some((userObj) => userObj.id === user.id));
		} else {
			filteredInfo = info;
		}
	}
</script>

<div class="flex flex-row h-full space-x-2">
	<div class="flex flex-col rounded-lg bg-white h-full w-full p-2 space-y-3 shadow-xl">
		<div
			class="flex flex-col items-center justify-center bg-gradient-to-r from-primary-500 to-secondary-400 text-white rounded-lg h-1/6 text-3xl font-semibold p-2 shadow-md"
		>
			<div class="flex flex-row justify-between w-3/4">
				<a class="sticky" href={prevMonth(year, month)}>
					<i class="fas fa-chevron-left" />
				</a>
				{#key month}
					<p in:fly={{ delay: 100, duration: 300 }}>
						{monthNames[month - 1].toUpperCase()}, {year}
					</p>
				{/key}
				<a href={nextMonth(year, month)}>
					<i class="fas fa-chevron-right" />
				</a>
			</div>
		</div>
		<div class="grid grid-cols-7 gap-5 font-semibold">
			{#each daysOfWeek as dayName}
				<div class="flex justify-center">
					{dayName}
				</div>
			{/each}
		</div>
		<div class="grid grid-cols-7 gap-1 h-full">
			{#if firstDay > 0}
				{#each Array.from({ length: firstDay - 1 }, (_, i) => i + 1) as day}
					<div class="" />
				{/each}
			{:else}
				{#each Array.from({ length: 6 }, (_, i) => i + 1) as day}
					<div class="" />
				{/each}
			{/if}
			{#each Array.from({ length: daysInMonth }, (_, i) => i + 1) as day}
				{#key filteredInfo}
					<Day {day} {month} {year} info={filteredInfo} />
				{/key}
			{/each}
		</div>
		<div class="flex flex-col bg-gradient-to-r from-primary-500 to-secondary-400 rounded-lg p-2">
			<div class="flex w-full h-full justify-between items-center">
				<a
					href={currentMonth()}
					class="font-light text-lg border rounded-lg border-white p-2 hover:bg-white text-white hover:text-primary-500 transition duration-300"
				>
					<i class="fas fa-calendar-day" />
					{m.today()}
				</a>
				<SlideToggle name="tasks-toggle" bind:checked={$showAllTasks} active="bg-green-500"
					><span class="text-white font-light text-lg">{m.showAllTasks()}</span></SlideToggle
				>
			</div>
		</div>
	</div>
</div>
