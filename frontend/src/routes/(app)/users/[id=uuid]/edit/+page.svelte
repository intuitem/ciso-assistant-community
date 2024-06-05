<script lang="ts">
	import type { PageData } from './$types';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { UserEditSchema } from '$lib/utils/schemas';
	import { page } from '$app/stores';
	import { breadcrumbObject } from '$lib/utils/stores';

	import * as m from '$paraglide/messages';

	export let data: PageData;
	breadcrumbObject.set(data.object);
</script>

<div class="card bg-white shadow p-4">
	<ModelForm form={data.form} schema={UserEditSchema} model={data.model} />
</div>
<div class="card bg-white shadow p-4 mt-2">
	<p class="text-gray-500 text-sm">
		{m.setTemporaryPassword1()}
		<a
			href="{$page.url.pathname}/set-password"
			class="text-primary-700 hover:text-primary-500"
			data-testid="set-password-btn">{m.setTemporaryPassword()}</a
		>. {m.setTemporaryPassword2()}.
	</p>
</div>
