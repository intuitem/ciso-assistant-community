<script lang="ts">
	import FormPreview from '#lib/components/QuickForms/FormPreview.svelte';
	import { m } from '#paraglide/messages.js';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<FormPreview initial={data.initial} hint={m.quickFormPreviewPublishedHint()}>
	{#snippet actions()}
		<a class="btn btn-sm preset-filled-primary-500" href={`/quick-forms/${data.quickFormId}`}>
			<i class="fa-solid fa-arrow-left mr-1"></i>{m.back()}
		</a>
	{/snippet}
</FormPreview>
