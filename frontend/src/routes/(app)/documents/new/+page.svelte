<script lang="ts">
	import { m } from '$paraglide/messages';
	import { goto } from '$app/navigation';
	import DocumentCreate from '$lib/components/DocumentEditor/DocumentCreate.svelte';
</script>

<div class="mx-auto max-w-2xl space-y-6 p-4 sm:p-6">
	<a
		href="/documents"
		class="inline-flex items-center gap-1.5 text-sm text-surface-500 transition-colors hover:text-primary-500"
	>
		<i class="fa-solid fa-arrow-left"></i>{m.documents()}
	</a>

	<!-- Header: spined card, matching the reader/catalog language -->
	<header
		class="relative overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 pl-7"
	>
		<span class="absolute inset-y-0 left-0 w-1.5 bg-primary-500"></span>
		<div class="flex items-center gap-4">
			<div
				class="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-primary-500/10 text-xl text-primary-500 ring-1 ring-primary-500/20"
			>
				<i class="fa-solid fa-file-circle-plus"></i>
			</div>
			<div>
				<h1 class="text-2xl font-bold leading-tight tracking-tight">{m.addDocumentContainer()}</h1>
				<p class="mt-0.5 text-sm text-surface-500">{m.newDocumentSubtitle()}</p>
			</div>
		</div>
	</header>

	<!-- Form sheet -->
	<div class="rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 shadow-sm sm:p-8">
		<DocumentCreate onCreated={(c) => goto(`/document-containers/${c.id}/document`)} />
	</div>
</div>
