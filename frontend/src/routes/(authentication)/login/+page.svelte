<script lang="ts">
	import type { ActionData, PageData } from './$types';
	import Logo from '$lib/components/Logo/Logo.svelte';
	import Greetings from './Greetings.svelte';
	import FormCard from './FormCard.svelte';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
</script>

<div class="lg:relative h-screen w-screen bg-slate-200">
	<div
		class="invisible lg:visible absolute top-5 left-1/2 transform -translate-x-1/2 top-5 left-5 transform-none"
	>
		<div class="flex justify-center justify-start flex-row max-w-48 space-x-4 pb-3">
			<Logo />
		</div>
	</div>
	<div class="lg:invisible pt-5 flex justify-center">
		<div class="flex justify-center flex-row max-w-48 space-x-4 pb-3">
			<Logo />
		</div>
	</div>
	<div
		class="lg:absolute lg:top-1/2 lg:left-1/2 w-full transform lg:-translate-x-1/2 lg:-translate-y-1/2"
	>
		<div class="flex flex-col lg:flex-row w-full lg:pr-8 space-y-4 lg:space-y-0 lg:space-x-4">
			<Greetings />
			<div class="flex justify-center lg:pr-5 items-center w-full lg:w-2/5">
				<FormCard {data} {form} />
			</div>
		</div>
	</div>
</div>
