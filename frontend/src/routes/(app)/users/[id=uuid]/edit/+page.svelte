<script lang="ts">
	import type { PageData } from './$types';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { UserEditSchema } from '$lib/utils/schemas';
	import { page } from '$app/stores';
	import { breadcrumbObject } from '$lib/utils/stores';

	export let data: PageData;
	breadcrumbObject.set(data.object);
</script>

<div class="card bg-white shadow p-4">
	<ModelForm form={data.form} schema={UserEditSchema} model={data.model} />
</div>
<div class="card bg-white shadow p-4 mt-2">
	<p class="text-gray-500 text-sm">
		In case the user cannot set their own password, you can <a
			href="{$page.url.pathname}/set-password"
			class="text-primary-700 hover:text-primary-500"
			data-testid="set-password-btn">set a temporary password</a
		>. Please use a strong one and make sure to inform the user to change it as soon as possible.
	</p>
</div>
