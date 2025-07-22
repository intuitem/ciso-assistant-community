<script lang="ts">
	import { run } from 'svelte/legacy';

	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData, ActionData } from './$types';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import * as m from '$paraglide/messages';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	run(() => {
		if (form && form.redirect) {
			goto(getSecureRedirect(form.redirect));
		}
	});
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2 justify-end">
			<form class="flex justify-end" action={`${page.url.pathname}/export`}>
				<button type="submit" class="btn preset-filled-primary-500 h-fit">
					<i class="fa-solid fa-download mr-2"></i>
					{m.exportButton()}
				</button>
			</form>
		</div>
	{/snippet}
</DetailView>
