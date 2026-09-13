<script lang="ts">
	import FrameworkBuilder from '$lib/components/FrameworkBuilder/FrameworkBuilder.svelte';
	import type { Framework } from '$lib/components/FrameworkBuilder/builder-state';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	let { data } = $props();

	const draft = $derived(data.draft);
	const editorData = $derived(data.editorData);
	const meta = $derived(editorData.editing_draft.framework_meta);

	$effect(() => {
		$pageTitle = m.lbQuickFormPageTitle({ name: meta.name || draft.name });
	});

	// Synthetic Framework prop: the editor works on the library document.
	// Pages are the nodes; the framework-only vocabulary is hidden by mode.
	const framework: Framework = $derived({
		id: editorData.quick_form_urn,
		name: meta.name ?? '',
		description: meta.description ?? null,
		annotation: meta.annotation ?? null,
		folder: { id: draft.folder?.id ?? '', str: draft.folder?.str ?? '' },
		library: null,
		min_score: 0,
		max_score: 100,
		scores_definition: meta.scores_definition ?? null,
		implementation_groups_definition: null,
		outcomes_definition: (meta.outcomes_definition as Framework['outcomes_definition']) ?? null,
		field_visibility: {},
		locale: meta.locale,
		translations: meta.translations ?? {},
		available_languages: meta.available_languages ?? [],
		urn: editorData.quick_form_urn,
		urn_namespace: meta.urn_namespace ?? 'custom',
		ref_id: meta.ref_id ?? null,
		editing_version: draft.identity_locked ? 2 : 1,
		has_compliance_assessments: editorData.has_responses ?? false
	});

	const apiTarget = $derived(
		`/experimental/library-builder/${draft.id}/quick-form?quick_form_urn=${encodeURIComponent(
			editorData.quick_form_urn
		)}`
	);

	const links = $derived({
		back: `/experimental/library-builder/${draft.id}`,
		// Shows the saved draft: the builder saves explicitly, so save before previewing.
		preview: `/experimental/library-builder/${draft.id}/quick-form/preview?quick_form_urn=${encodeURIComponent(
			editorData.quick_form_urn
		)}`
	});
</script>

<div class="min-h-screen">
	{#key draft.id}
		<FrameworkBuilder
			{framework}
			requirementNodes={[]}
			questions={[]}
			editingDraft={editorData.editing_draft}
			{apiTarget}
			{links}
			mode="quick_form"
		/>
	{/key}
</div>
