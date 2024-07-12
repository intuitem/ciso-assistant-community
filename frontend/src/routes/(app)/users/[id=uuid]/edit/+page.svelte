<script lang="ts">
	import type { PageData } from './$types';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { UserEditSchema } from '$lib/utils/schemas';
	import { page } from '$app/stores';
	import { breadcrumbObject } from '$lib/utils/stores';

	import * as m from '$paraglide/messages';
	import { goto } from '$app/navigation';

	export let data: PageData;
	breadcrumbObject.set(data.object);

	let debugStyle = "";
	let debugClicked = false;
	$: if (debugClicked) {
		debugStyle = "border: 50px solid violet;";
	} else {
		debugStyle = "";
	}
	let debugCodeElem = null;
	let debugText = "...";
</script>

<code style="font-size: 32px;border: 10px solid blue;" bind:this={debugCodeElem}>{debugText}</code>
<div class="card bg-white shadow p-4">
	<ModelForm form={data.form} schema={UserEditSchema} model={data.model} />
</div>
<div style={debugStyle} class="card bg-white shadow p-4 mt-2">
	<p class="text-gray-500 text-sm">
		{m.setTemporaryPassword1()}
		<a
			href="{$page.url.pathname}/set-password"
			class="text-primary-700 hover:text-primary-500"
			data-testid="set-password-btn" on:click={(e) => {
				debugClicked=!debugClicked;
				goto(`${$page.url.pathname}/set-password`).then(
					res => {debugText = `[THEN] ${res}`;}
				).catch(
					err => {debugText = `[CATCH] ${err}`;}
				);
			}}>{m.setTemporaryPassword()}</a
		>. {m.setTemporaryPassword2()}.
	</p>
</div>
