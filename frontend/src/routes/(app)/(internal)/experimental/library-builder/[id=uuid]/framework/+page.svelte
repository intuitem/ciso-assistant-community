<script lang="ts">
	import FrameworkBuilder from '$lib/components/FrameworkBuilder/FrameworkBuilder.svelte';
	import type { Framework } from '$lib/components/FrameworkBuilder/builder-state';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	let { data } = $props();

	// $derived, not const: same-route navigation (draft A's editor → draft
	// B's editor) reuses this component with new `data`. Snapshots would keep
	// the editor saving against the previous draft.
	const draft = $derived(data.draft);
	const editorData = $derived(data.editorData);
	const meta = $derived(editorData.editing_draft.framework_meta);

	$effect(() => {
		$pageTitle = m.lbFrameworkPageTitle({ name: meta.name || draft.name });
	});

	// Synthetic Framework prop: the editor works on the library document, so
	// there is no live Framework row backing it. The framework URN doubles as
	// the stable id (localStorage keys, slug fallback).
	const framework: Framework = $derived({
		id: editorData.framework_urn,
		name: meta.name ?? '',
		description: meta.description ?? null,
		annotation: meta.annotation ?? null,
		folder: { id: draft.folder?.id ?? '', str: draft.folder?.str ?? '' },
		library: null,
		min_score: meta.min_score ?? 0,
		max_score: meta.max_score ?? 100,
		scores_definition: meta.scores_definition ?? null,
		implementation_groups_definition: meta.implementation_groups_definition ?? null,
		outcomes_definition: (meta.outcomes_definition as Framework['outcomes_definition']) ?? null,
		field_visibility: meta.field_visibility ?? {},
		locale: meta.locale,
		translations: meta.translations ?? {},
		available_languages: meta.available_languages ?? [],
		urn: editorData.framework_urn,
		urn_namespace: meta.urn_namespace ?? 'custom',
		ref_id: meta.ref_id ?? null,
		// Drives the Live/Draft toolbar badge: once the library has been
		// published, the loaded framework is the live content.
		editing_version: draft.identity_locked ? 2 : 1,
		has_compliance_assessments: editorData.has_compliance_assessments ?? false
	});

	const apiTarget = $derived(
		`/experimental/library-builder/${draft.id}/framework?framework_urn=${encodeURIComponent(
			editorData.framework_urn
		)}`
	);

	const links = $derived({
		back: `/experimental/library-builder/${draft.id}`,
		preview: null
		// No exportYaml: export is a whole-library action, offered on the
		// library page, not inside the framework editor.
	});
</script>

<div class="min-h-screen">
	<!-- FrameworkBuilder seeds its store from initial props only: remount it
	     whenever the underlying draft changes. -->
	{#key draft.id}
		<FrameworkBuilder
			{framework}
			requirementNodes={[]}
			questions={[]}
			editingDraft={editorData.editing_draft}
			{apiTarget}
			{links}
		/>
	{/key}
</div>
