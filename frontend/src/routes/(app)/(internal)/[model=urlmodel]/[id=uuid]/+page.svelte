<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData, ActionData } from './$types';
	import { goto } from '$app/navigation';
	import { getSecureRedirect } from '$lib/utils/helpers';

	export let data: PageData;
	export let form: ActionData;

	let displaySecurityObjective = false;

	if (data.urlModel === 'assets') {
		displaySecurityObjective = true;
	}

	$: if (form && form.redirect) {
		goto(getSecureRedirect(form.redirect));
	}
</script>

<DetailView {data} {displaySecurityObjective} />
