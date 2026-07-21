<script lang="ts">
	import { m } from '$paraglide/messages';
	import { enhance } from '$app/forms';
	import { superForm, defaults } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import type { PageData } from './$types';

	let { data, form }: { data: PageData; form: { error?: string; result?: any } | null } = $props();

	let submitting = $state(false);

	// Local SPA superForm purely to host the form-coupled FolderTreeSelect; the
	// selected value is mirrored into the multipart form via a hidden input.
	const _folderForm = superForm(defaults(zod(z.object({ folder: z.string().default('') }))), {
		SPA: true,
		validators: zod(z.object({ folder: z.string() }))
	});
	const { form: folderData } = _folderForm;
</script>

<div class="mx-auto max-w-2xl space-y-6 p-4 sm:p-6">
	<a
		href="/document-templates"
		class="inline-flex items-center gap-1.5 text-sm text-surface-500 transition-colors hover:text-primary-500"
	>
		<i class="fa-solid fa-arrow-left"></i>{m.documentTemplates()}
	</a>

	<!-- Header: spined card, matching the documents pages -->
	<header
		class="relative overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 pl-7"
	>
		<span class="absolute inset-y-0 left-0 w-1.5 bg-primary-500"></span>
		<div class="flex items-center gap-4">
			<div
				class="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-primary-500/10 text-xl text-primary-500 ring-1 ring-primary-500/20"
			>
				<i class="fa-solid fa-file-import"></i>
			</div>
			<div>
				<h1 class="text-2xl font-bold leading-tight tracking-tight">{m.importTemplates()}</h1>
				<p class="mt-0.5 text-sm text-surface-500">{m.importTemplatesSubtitle()}</p>
			</div>
		</div>
	</header>

	{#if form?.error}
		<aside class="variant-soft-error rounded-lg p-3 text-sm">{form.error}</aside>
	{/if}

	{#if form?.result}
		<aside class="variant-soft-success space-y-2 rounded-lg p-3 text-sm">
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

	<!-- Form sheet -->
	<div class="rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 shadow-sm sm:p-8">
		<p class="text-sm leading-relaxed text-surface-600-400">{m.importTemplatesHelp()}</p>
		<aside
			class="mt-4 mb-6 flex items-start gap-2.5 rounded-lg border border-surface-200-800 bg-surface-100-900/40 p-3 text-sm text-surface-600-400"
		>
			<i class="fa-solid fa-circle-info mt-0.5 text-primary-500"></i>
			<span>{m.importTemplatesSingleNote()}</span>
		</aside>

		<form
			method="POST"
			enctype="multipart/form-data"
			class="space-y-5"
			use:enhance={() => {
				submitting = true;
				return async ({ update }) => {
					await update({ reset: false });
					submitting = false;
				};
			}}
		>
			<FolderTreeSelect form={_folderForm} field="folder" label={m.domain()} />
			<input type="hidden" name="folder" value={$folderData.folder ?? ''} />

			<label class="label">
				<span>{m.file()} (.zip)</span>
				<input name="file" type="file" accept=".zip" class="input" required />
			</label>

			<button
				type="submit"
				class="btn variant-filled-primary w-full font-semibold shadow-sm transition-shadow hover:shadow-md"
				disabled={submitting || !$folderData.folder}
			>
				{#if submitting}
					<i class="fa-solid fa-spinner fa-spin mr-2"></i>
				{:else}
					<i class="fa-solid fa-file-import mr-2"></i>
				{/if}
				{m.importTemplates()}
			</button>
		</form>
	</div>
</div>
