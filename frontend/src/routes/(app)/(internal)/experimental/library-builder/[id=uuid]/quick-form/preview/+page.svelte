<script lang="ts">
	import FormPreview from '$lib/components/QuickForms/FormPreview.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<FormPreview
	initial={data.initial}
	payload={{ urn: data.quickFormUrn ?? null }}
	hint={m.lbQuickFormPreviewHint()}
>
	{#snippet actions()}
		<a
			class="btn btn-sm preset-tonal-primary"
			href={`/experimental/library-builder/${data.draftId}/quick-form?quick_form_urn=${encodeURIComponent(data.quickFormUrn)}`}
		>
			<i class="fa-solid fa-pen mr-1"></i>{m.lbBackToEditor()}
		</a>
	{/snippet}
</FormPreview>
