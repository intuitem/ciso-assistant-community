<script lang="ts">
	import { m } from '$paraglide/messages';
	import { enhance } from '$app/forms';
	import type { PageData } from './$types';

	let { data, form }: { data: PageData; form: { error?: string; result?: any } | null } = $props();

	let submitting = $state(false);
</script>

<div class="mx-auto max-w-xl space-y-6 p-4 sm:p-6">
	<a href="/document-templates" class="text-sm text-primary-500 hover:underline">
		<i class="fa-solid fa-arrow-left mr-1"></i>{m.documentTemplates()}
	</a>
	<div>
		<h1 class="text-2xl font-bold">{m.importTemplates()}</h1>
		<p class="mt-1 text-sm text-surface-500">{m.importTemplatesHelp()}</p>
	</div>

	{#if form?.error}
		<aside class="variant-soft-error rounded p-3 text-sm">{form.error}</aside>
	{/if}

	{#if form?.result}
		<aside class="variant-soft-success space-y-2 rounded p-3 text-sm">
			<p class="font-medium">
				<i class="fa-solid fa-check mr-1"></i>{m.templatesImported({
					created: form.result.created,
					updated: form.result.updated
				})}
			</p>
			{#if form.result.errors?.length}
				<ul class="list-disc pl-5 text-error-600-400">
					{#each form.result.errors as e}<li>{e}</li>{/each}
				</ul>
			{/if}
			<a href="/document-templates" class="inline-block text-primary-500 hover:underline">
				{m.documentTemplates()}
			</a>
		</aside>
	{/if}

	<form
		method="POST"
		enctype="multipart/form-data"
		class="space-y-4"
		use:enhance={() => {
			submitting = true;
			return async ({ update }) => {
				await update({ reset: false });
				submitting = false;
			};
		}}
	>
		<label class="label">
			<span>{m.domain()}</span>
			<select name="folder" class="select" required>
				<option value="" disabled selected>—</option>
				{#each data.folders as f (f.id)}
					<option value={f.id}>{f.name}</option>
				{/each}
			</select>
		</label>

		<label class="label">
			<span>{m.file()} (.zip)</span>
			<input name="file" type="file" accept=".zip" class="input" required />
		</label>

		<button type="submit" class="btn variant-filled-primary" disabled={submitting}>
			{#if submitting}<i class="fa-solid fa-spinner fa-spin mr-2"></i>{/if}
			{m.importTemplates()}
		</button>
	</form>
</div>
