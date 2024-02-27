<script lang="ts">
	import { fly } from 'svelte/transition';
	import Day from './Day.svelte';
	import Notifications from './Notifications.svelte';
	import { showNotification } from '$lib/utils/stores';

	import * as m from '$paraglide/messages';

	export let info: object[];

	let showNotificationBool = JSON.parse($showNotification);

	let today = new Date();
	let month = today.getMonth() + 1;
	let year = today.getFullYear();
	let daysInMonth = new Date(year, month, 0).getDate();
	let firstDay = new Date(year, month - 1, 1).getDay();

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

	function todayDay() {
		month = today.getMonth() + 1;
		year = today.getFullYear();
		daysInMonth = new Date(year, month, 0).getDate();
		firstDay = new Date(year, month - 1, 1).getDay();
	}

	function nextMonth() {
		if (month == 12) {
			month = 1;
			year += 1;
		} else {
			month += 1;
		}
		daysInMonth = new Date(year, month, 0).getDate();
		firstDay = new Date(year, month - 1, 1).getDay();
	}

	function prevMonth() {
		if (month == 1) {
			month = 12;
			year -= 1;
		} else {
			month -= 1;
		}
		daysInMonth = new Date(year, month, 0).getDate();
		firstDay = new Date(year, month - 1, 1).getDay();
	}

	function notification() {
		showNotificationBool = !showNotificationBool;
		showNotification.set(showNotificationBool.toString());
	}
</script>

<div class="flex flex-row h-full space-x-2">
	<div class="flex flex-col rounded-lg bg-white h-full w-full p-2 space-y-3 shadow-xl">
		<div
			class="flex flex-col items-center justify-center bg-gradient-to-r from-primary-500 to-secondary-400 text-white rounded-lg h-1/6 text-3xl font-semibold p-2 shadow-md"
		>
			<div class="flex flex-row justify-between w-3/4">
				<button class="sticky" on:click={prevMonth}>
					<i class="fas fa-chevron-left" />
				</button>
				{#key month}
					<p in:fly={{ delay: 100, duration: 300 }}>
						{monthNames[month - 1].toUpperCase()}, {year}
					</p>
				{/key}
				<button on:click={nextMonth}>
					<i class="fas fa-chevron-right" />
				</button>
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
				<Day {day} {month} {year} {info} />
			{/each}
		</div>
		<div class="flex flex-col bg-gradient-to-r from-primary-500 to-secondary-400 rounded-lg p-2">
			<div class="flex w-full h-full justify-between items-start">
				<button
					on:click={todayDay}
					class="font-light text-lg border rounded-lg border-white p-2 hover:bg-white text-white hover:text-primary-500 transition duration-300"
				>
					<i class="fas fa-calendar-day" />
					{m.today()}
				</button>
				<!-- <button
					on:click={notification}
					class="font-light text-lg border rounded-lg border-white p-2 hover:bg-white text-white hover:text-secondary-400 transition duration-300"
				>
					<i class="fa-solid fa-envelope" />
					Notifications
				</button> -->
			</div>
		</div>
	</div>
	<!-- {#if showNotificationBool}
		<Notifications {info} />
	{/if} -->
</div>
