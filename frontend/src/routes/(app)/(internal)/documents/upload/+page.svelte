<script lang="ts">
	import { m } from '$paraglide/messages';
	import { enhance } from '$app/forms';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import type { PageData } from './$types';

	let { data, form }: { data: PageData; form: { error?: string } | null } = $props();

	const DOC_TYPES = ['policy', 'procedure', 'charter', 'record', 'meeting_minutes', 'other'];
	const TYPE_LABEL: Record<string, () => string> = {
		policy: m.policy,
		procedure: m.procedure,
		charter: m.charter,
		record: m.record,
		meeting_minutes: m.meetingMinutes,
		other: m.other
	};

	let submitting = $state(false);
</script>

<div class="mx-auto max-w-xl space-y-6 p-4">
	<a href="/documents" class="text-sm text-primary-500 hover:underline">
		<i class="fa-solid fa-arrow-left mr-1"></i>{m.documents()}
	</a>
	<h1 class="text-2xl font-bold">{m.uploadDocument()}</h1>

	{#if form?.error}
		<aside class="variant-soft-error rounded p-3 text-sm">{form.error}</aside>
	{/if}

	<form
		method="POST"
		enctype="multipart/form-data"
		class="space-y-4"
		use:enhance={() => {
			submitting = true;
			return async ({ update }) => {
				await update();
				submitting = false;
			};
		}}
	>
		<label class="label">
			<span>{m.name()}</span>
			<input name="name" type="text" class="input" placeholder={m.untitled()} />
		</label>

		<label class="label">
			<span>{m.documentType()}</span>
			<select name="document_type" class="select">
				{#each DOC_TYPES as t}
					<option value={t}>{TYPE_LABEL[t]()}</option>
				{/each}
			</select>
		</label>

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
			<span>{m.language()}</span>
			<select name="locale" class="select">
				{#each Object.entries(LOCALE_MAP) as [code, info]}
					<option value={code} selected={code === 'en'}>{info.name}</option>
				{/each}
			</select>
		</label>

		<label class="label">
			<span>{m.file()}</span>
			<input name="file" type="file" class="input" required />
		</label>

		<button type="submit" class="btn variant-filled-primary" disabled={submitting}>
			{#if submitting}<i class="fa-solid fa-spinner fa-spin mr-2"></i>{/if}
			{m.upload()}
		</button>
	</form>
</div>
