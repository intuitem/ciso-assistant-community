<script lang="ts">
	import { filesProxy, formFieldProxy } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';
	let { form, existing = 0 }: { form: any; existing?: number } = $props();
	const files = filesProxy(form, 'attachments');
	const { errors } = formFieldProxy(form, 'attachments');
	let input: HTMLInputElement | undefined = $state();
	const selected = $derived(Array.from($files ?? []));
	const tooMany = $derived(existing + selected.length > 10);
	$effect(() => input?.setCustomValidity(tooMany ? m.evidenceFilesLimit() : ''));
	function remove(index: number) {
		const transfer = new DataTransfer();
		selected.forEach((file, i) => {
			if (i !== index) transfer.items.add(file);
		});
		$files = transfer.files;
	}
	function paste(event: ClipboardEvent) {
		if (!event.clipboardData?.files.length) return;
		const transfer = new DataTransfer();
		for (const file of [...selected, ...Array.from(event.clipboardData.files)])
			transfer.items.add(file);
		$files = transfer.files;
		event.preventDefault();
	}
</script>

<svelte:document onpaste={paste} />

<div>
	<label for="evidence-files" class="text-sm font-semibold">{m.attachments()}</label>
	<input
		id="evidence-files"
		name="attachments"
		type="file"
		multiple
		class="input"
		bind:files={$files}
		bind:this={input}
		aria-describedby="evidence-files-help"
		aria-invalid={tooMany || !!$errors}
		data-testid="form-input-attachments"
	/>
	<p id="evidence-files-help" class="text-sm text-surface-600-400">
		{m.evidenceFilesHelp()} ({existing + selected.length}/10)
	</p>
	{#if tooMany}<p class="text-error-500" role="alert">{m.evidenceFilesLimit()}</p>{/if}
	{#each $errors ?? [] as error}<p class="text-error-500" role="alert">{error}</p>{/each}
	<ul class="space-y-1">
		{#each selected as file, index}
			<li class="flex items-center justify-between gap-2">
				<span class="break-all">{file.name}</span>
				<button
					type="button"
					class="btn btn-sm"
					onclick={() => remove(index)}
					aria-label={`${m.delete()}: ${file.name}`}><i class="fa-solid fa-xmark"></i></button
				>
			</li>
		{/each}
	</ul>
</div>
