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
</script>

<DetailView {data}>
  <div slot="actions" class="flex flex-col space-y-2 justify-end">
			<form class="flex justify-end" action={`${$page.url.pathname}/export`}>
				<button type="submit" class="btn variant-filled-primary h-fit" >
          <i class="fa-solid fa-download mr-2" /> {m.exportButton()}
        </button>
			</form>
  </div>
</DetailView>
