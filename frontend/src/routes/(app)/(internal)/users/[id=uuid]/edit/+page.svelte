<script lang="ts">
	import { page } from '$app/state';
	import ModelForm from '$lib/components/Forms/ModelForm.svelte';
	import { UserEditSchema } from '$lib/utils/schemas';
	import type { PageData } from './$types';

	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const isAdmin = $derived(Boolean(page.data.user?.is_admin));
	const isSelf = $derived(page.data.user?.id === data.object.id);
	const showDisableMFA = $derived(isAdmin && !isSelf && data.object.has_mfa_enabled);
</script>

<div class="card bg-surface-50-950 shadow-sm p-4">
	<ModelForm form={data.form} schema={UserEditSchema} model={data.model} />
</div>

{#if data.object.is_local}
	<div class="card bg-surface-50-950 shadow-sm p-4 mt-2">
		<p class="text-surface-600-400 text-sm">
			{m.setTemporaryPassword1()}
			<a
				href="{page.url.pathname}/set-password"
				class="text-primary-700 hover:text-primary-500"
				data-testid="set-password-btn">{m.setTemporaryPassword()}</a
			>. {m.setTemporaryPassword2()}.
		</p>
	</div>
{/if}

{#if showDisableMFA}
	<div class="card bg-white shadow-sm p-4 mt-2">
		<p class="text-gray-500 text-sm">
			{m.disableMFA1()}
			<a
				href="{page.url.pathname}/disable-mfa"
				class="text-primary-700 hover:text-primary-500"
				data-testid="disable-mfa-btn">{m.disableMFALinkText()}</a
			>. {m.disableMFA2()}.
		</p>
	</div>
{/if}
