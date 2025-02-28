<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData, ActionData } from './$types';
	import { goto } from '$app/navigation';
  import { page } from '$app/stores';
	import { getSecureRedirect } from '$lib/utils/helpers';
  import * as m from '$paraglide/messages';

	export let data: PageData;
	export let form: ActionData;

	$: if (form && form.redirect) {
		goto(getSecureRedirect(form.redirect));
	}

	function handleExportSubmit(event: Event) {
		if (data.has_out_of_scope_objects) {
			const confirmed = confirm("Warning: Some objects are out of scope. Do you want to continue?");
			if (!confirmed) {
				event.preventDefault(); // Prevent the form submission if canceled
			}
		}
	}
</script>

<DetailView {data}>
	<div slot="actions" class="flex flex-col space-y-2 justify-end">
		<!-- Use the submit event instead of the click event on the button -->
		<form class="flex justify-end" action={`${$page.url.pathname}/export`} on:submit={handleExportSubmit}>
			<button type="submit" class="btn variant-filled-primary h-fit">
				<i class="fa-solid fa-download mr-2" /> {m.exportButton()}
			</button>
		</form>
	</div>
</DetailView>
