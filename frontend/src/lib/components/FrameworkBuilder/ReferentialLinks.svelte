<script lang="ts">
	import {
		getBuilderContext,
		getReferentialCatalogContext,
		slugifyFrameworkName,
		inlineCopyFromCatalogEntry,
		makeInlineReferential,
		referentialLabel,
		getTranslation,
		setInlineReferentialTranslation,
		type BuilderNode,
		type InlineReferential,
		type ReferentialCatalogEntry
	} from './builder-state';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { tick } from 'svelte';

	interface Props {
		node: BuilderNode;
		kind: 'reference_controls' | 'threats';
	}

	let { node, kind }: Props = $props();

	const builder = getBuilderContext();
	const { framework: frameworkStore, activeLanguage: activeLanguageStore } = builder;
	const catalog = getReferentialCatalogContext();

	const isControl = kind === 'reference_controls';
	const inlineKey = isControl ? 'inline_reference_controls' : 'inline_threats';
	const urnType = isControl ? 'reference_control' : 'threat';
	// Reference-control category / CSF function choices, matching
	// ReferenceControl.CATEGORY and ReferenceControl.CSF_FUNCTION on the backend.
	const CATEGORIES = ['policy', 'process', 'technical', 'physical', 'procedure'];
	const CSF_FUNCTIONS = ['govern', 'identify', 'protect', 'detect', 'respond', 'recover'];

	let adding = $state(false);
	let tab: 'existing' | 'inline' = $state('existing');
	let search = $state('');
	let newRefId = $state('');
	let newName = $state('');
	let newCategory = $state('');
	let newCsfFunction = $state('');
	let newDescription = $state('');
	let newAnnotation = $state('');
	// Typical evidence as discrete items (doc-pol list shape).
	let newTypicalEvidence = $state<string[]>([]);

	const currentUrns = $derived((node.node[kind] ?? []) as string[]);
	const catalogEntries = $derived(
		isControl ? catalog.referenceControls : catalog.threats
	) as ReferentialCatalogEntry[];
	const inlineEntries = $derived(($frameworkStore[inlineKey] ?? []) as InlineReferential[]);

	// Inline-defined referentials linked to this node: their name/description/
	// annotation are translatable here. Library-referenced objects are excluded —
	// their translations come from their own library.
	const translatableLinked = $derived(
		inlineEntries.filter((e) => e.urn && currentUrns.includes(e.urn))
	);

	function saveInlineTranslation(id: string, field: string, value: string) {
		const lang = $activeLanguageStore;
		if (!lang) return;
		builder.updateFramework({
			[inlineKey]: setInlineReferentialTranslation(inlineEntries, id, lang, field, value)
		});
	}

	// Labels for framework-local inline objects (few); the large server catalog is
	// indexed once in the shared context (`catalog.labelByUrn`).
	const inlineLabelByUrn = $derived.by(() => {
		const map = new Map<string, string>();
		for (const e of inlineEntries) if (e.urn) map.set(e.urn, referentialLabel(e));
		return map;
	});

	function labelFor(urn: string): string {
		return inlineLabelByUrn.get(urn) ?? catalog.labelByUrn?.get(urn) ?? urn;
	}

	const linkableEntries = $derived.by(() => {
		const linked = new Set(currentUrns);
		const term = search.trim().toLowerCase();
		return catalogEntries
			.filter((e) => e.urn && !linked.has(e.urn))
			.filter(
				(e) =>
					!term ||
					(e.name ?? '').toLowerCase().includes(term) ||
					(e.ref_id ?? '').toLowerCase().includes(term) ||
					e.urn.toLowerCase().includes(term)
			)
			.slice(0, 50);
	});

	function addUrn(urn: string) {
		if (currentUrns.includes(urn)) return;
		builder.updateNode(node.node.id, { [kind]: [...currentUrns, urn] });
	}

	// Picking an existing instance object: reference it only if it comes from a
	// builtin library (present in any target instance); otherwise copy it into
	// this framework as an inline object so the export stays self-contained.
	function pickExisting(entry: ReferentialCatalogEntry) {
		if (entry.referenceable) {
			addUrn(entry.urn);
			return;
		}
		const copy = inlineCopyFromCatalogEntry(entry, {
			urnType,
			namespace: $frameworkStore.urn_namespace || 'custom',
			slug: frameworkSlug(),
			isControl
		});
		// Deterministic URN dedups repeated picks of the same source into one copy.
		if (!inlineEntries.some((e) => e.urn === copy.urn)) {
			builder.updateFramework({ [inlineKey]: [...inlineEntries, copy] });
		}
		addUrn(copy.urn);
	}

	function removeUrn(urn: string) {
		builder.updateNode(node.node.id, { [kind]: currentUrns.filter((u) => u !== urn) });
	}

	let evidenceListEl: HTMLDivElement | undefined = $state();

	function addEvidence() {
		newTypicalEvidence = [...newTypicalEvidence, ''];
	}

	function removeEvidence(index: number) {
		newTypicalEvidence = newTypicalEvidence.filter((_, i) => i !== index);
	}

	// Enter on a non-empty input adds the next one; Backspace on an empty input
	// deletes the row. Mirrors the question-choice editor.
	async function handleEvidenceKeydown(e: KeyboardEvent, index: number) {
		const input = e.currentTarget as HTMLInputElement;
		const focusLast = async () => {
			await tick();
			const inputs = evidenceListEl?.querySelectorAll<HTMLInputElement>('.evidence-item-input');
			inputs?.[inputs.length - 1]?.focus();
		};
		if (e.key === 'Enter') {
			e.preventDefault();
			if (!input.value.trim()) return;
			addEvidence();
			await focusLast();
		} else if (e.key === 'Backspace' && !input.value) {
			e.preventDefault();
			removeEvidence(index);
			await tick();
			const inputs = evidenceListEl?.querySelectorAll<HTMLInputElement>('.evidence-item-input');
			if (inputs && inputs.length > 0) {
				inputs[Math.min(index, inputs.length - 1)]?.focus();
			}
		}
	}

	function frameworkSlug(): string {
		const fw = $frameworkStore;
		return fw.ref_id && fw.ref_id.length > 0 ? fw.ref_id : slugifyFrameworkName(fw.name, fw.id);
	}

	function createInline() {
		const refId = newRefId.trim();
		if (!refId) return;
		// Trimmed, non-empty evidence items → list (matches doc-pol); null if none.
		const evidence = newTypicalEvidence.map((item) => item.trim()).filter(Boolean);
		// No sourceKey: a hand-defined ref_id is the user's chosen identity.
		const entry = makeInlineReferential({
			namespace: $frameworkStore.urn_namespace || 'custom',
			slug: frameworkSlug(),
			urnType,
			isControl,
			refId,
			name: newName.trim() || null,
			description: newDescription.trim() || null,
			annotation: newAnnotation.trim() || null,
			category: newCategory || null,
			csfFunction: newCsfFunction || null,
			typicalEvidence: evidence.length ? evidence : null
		});
		builder.updateFramework({ [inlineKey]: [...inlineEntries, entry] });
		addUrn(entry.urn);
		newRefId = '';
		newName = '';
		newCategory = '';
		newCsfFunction = '';
		newDescription = '';
		newAnnotation = '';
		newTypicalEvidence = [];
		adding = false;
	}
</script>

{#if $activeLanguageStore}
	{@const lang = $activeLanguageStore}
	<!-- Translation mode: edit translations of the inline referentials linked here.
	     Each field shows the source (read-only) beside its translation input. -->
	{#snippet translationField(
		entry: InlineReferential,
		field: 'name' | 'description' | 'annotation',
		label: string,
		placeholder: string,
		multiline: boolean,
		lang: string
	)}
		{@const source = entry[field] ?? ''}
		<label class="text-[10px] font-semibold uppercase tracking-wider text-gray-500 block">
			{label}
			{#if source && !getTranslation(entry.translations, lang, field)}
				<span class="text-amber-500 ml-1" title={m.builderNotTranslated()}>*</span>
			{/if}
		</label>
		<div class="grid grid-cols-2 gap-2">
			{#if multiline}
				<textarea
					readonly
					rows="2"
					value={source}
					class="text-xs bg-transparent border border-gray-200 rounded px-2 py-1 text-gray-500 cursor-default resize-none"
				></textarea>
				<textarea
					rows="2"
					value={getTranslation(entry.translations, lang, field)}
					{placeholder}
					class="text-xs border border-gray-200 rounded px-2 py-1 resize-none"
					onblur={(e) => saveInlineTranslation(entry.id, field, e.currentTarget.value)}
				></textarea>
			{:else}
				<input
					type="text"
					readonly
					value={source}
					class="text-xs bg-transparent border border-gray-200 rounded px-2 py-1 text-gray-500 cursor-default"
				/>
				<input
					type="text"
					value={getTranslation(entry.translations, lang, field)}
					{placeholder}
					class="text-xs border border-gray-200 rounded px-2 py-1"
					onblur={(e) => saveInlineTranslation(entry.id, field, e.currentTarget.value)}
				/>
			{/if}
		</div>
	{/snippet}
	{#if translatableLinked.length}
		<div class="px-4 py-2 border-b border-gray-100 space-y-2">
			<span class="text-xs text-gray-500">
				{isControl ? m.builderReferenceControlsLabel() : m.builderThreatsLabel()}
			</span>
			{#each translatableLinked as entry (entry.urn)}
				<div class="p-2 border border-gray-200 rounded bg-gray-50 space-y-1">
					<div class="text-[10px] font-mono text-gray-400">{entry.ref_id ?? entry.urn}</div>
					{@render translationField(entry, 'name', m.name(), m.builderTranslateName(), false, lang)}
					{@render translationField(
						entry,
						'description',
						m.description(),
						m.builderTranslateDescription(),
						true,
						lang
					)}
					{#if entry.annotation}
						{@render translationField(
							entry,
							'annotation',
							m.annotation(),
							m.builderTranslateAnnotation(),
							true,
							lang
						)}
					{/if}
				</div>
			{/each}
		</div>
	{/if}
{:else}
	<div class="px-4 py-2 border-b border-gray-100">
		<div class="flex items-center flex-wrap gap-1">
			<span class="text-xs text-gray-500 mr-1">
				{isControl ? m.builderReferenceControlsLabel() : m.builderThreatsLabel()}
			</span>
			{#each currentUrns as urn (urn)}
				<span
					class="inline-flex items-center text-xs px-2 py-0.5 rounded-full border bg-blue-50 border-blue-200 text-blue-700"
				>
					{labelFor(urn)}
					<button
						type="button"
						class="ml-1 text-blue-400 hover:text-blue-700"
						aria-label={m.remove()}
						onclick={() => removeUrn(urn)}
					>
						<i class="fa-solid fa-xmark"></i>
					</button>
				</span>
			{/each}
			<button
				type="button"
				class="text-xs px-2 py-0.5 rounded-full border border-dashed border-gray-300 text-gray-400 hover:text-gray-600 hover:border-gray-400"
				onclick={() => (adding = !adding)}
			>
				<i class="fa-solid fa-plus mr-1"></i>{isControl
					? m.builderAddReferenceControl()
					: m.builderAddThreat()}
			</button>
		</div>

		{#if adding}
			<div class="mt-2 p-2 border border-gray-200 rounded bg-gray-50">
				<div class="flex gap-2 mb-2 text-xs">
					<button
						type="button"
						class="px-2 py-0.5 rounded {tab === 'existing'
							? 'bg-blue-100 text-blue-700'
							: 'text-gray-500'}"
						onclick={() => (tab = 'existing')}
					>
						{isControl ? m.builderLinkExistingControl() : m.builderLinkExistingThreat()}
					</button>
					<button
						type="button"
						class="px-2 py-0.5 rounded {tab === 'inline'
							? 'bg-blue-100 text-blue-700'
							: 'text-gray-500'}"
						onclick={() => (tab = 'inline')}
					>
						{isControl ? m.builderDefineInlineControl() : m.builderDefineInlineThreat()}
					</button>
				</div>

				{#if tab === 'existing'}
					<input
						type="text"
						class="w-full text-xs px-2 py-1 border border-gray-200 rounded mb-1"
						placeholder={m.search()}
						bind:value={search}
					/>
					<ul class="max-h-40 overflow-y-auto">
						{#each linkableEntries as entry (entry.urn)}
							{@const lib =
								entry.library && typeof entry.library === 'object'
									? (entry.library.name ?? entry.library.str)
									: entry.library}
							<li>
								<button
									type="button"
									class="w-full text-left text-xs px-2 py-1 hover:bg-blue-50 rounded flex items-center gap-2"
									onclick={() => pickExisting(entry)}
								>
									<span class="min-w-0 flex-1 truncate">
										<span class="font-medium">{entry.ref_id ?? entry.name ?? entry.urn}</span>
										{#if entry.ref_id && entry.name}<span class="ml-1.5 text-gray-500"
												>{entry.name}</span
											>{/if}
									</span>
									<span class="shrink-0 text-[10px] text-gray-400">
										{entry.referenceable && lib ? lib : m.builderWillBeCopied()}
									</span>
								</button>
							</li>
						{:else}
							<li class="text-xs text-gray-400 px-2 py-1">{m.builderNoCatalogMatches()}</li>
						{/each}
					</ul>
				{:else}
					<div class="space-y-1">
						<div class="flex flex-wrap gap-1 items-center">
							<input
								type="text"
								class="text-xs px-2 py-1 border border-gray-200 rounded w-24"
								placeholder={m.refId()}
								bind:value={newRefId}
							/>
							<input
								type="text"
								class="text-xs px-2 py-1 border border-gray-200 rounded flex-1 min-w-32"
								placeholder={m.name()}
								bind:value={newName}
							/>
							{#if isControl}
								<select
									class="text-xs px-2 py-1 border border-gray-200 rounded"
									title={m.category()}
									bind:value={newCategory}
								>
									<option value="">{m.category()}: —</option>
									{#each CATEGORIES as cat}
										<option value={cat}>{safeTranslate(cat)}</option>
									{/each}
								</select>
								<select
									class="text-xs px-2 py-1 border border-gray-200 rounded"
									title={m.csfFunction()}
									bind:value={newCsfFunction}
								>
									<option value="">{m.csfFunction()}: —</option>
									{#each CSF_FUNCTIONS as fn}
										<option value={fn}>{safeTranslate(fn)}</option>
									{/each}
								</select>
							{/if}
						</div>
						<textarea
							class="w-full text-xs px-2 py-1 border border-gray-200 rounded"
							rows="2"
							placeholder={m.description()}
							bind:value={newDescription}
						></textarea>
						<textarea
							class="w-full text-xs px-2 py-1 border border-gray-200 rounded"
							rows="2"
							placeholder={m.annotation()}
							bind:value={newAnnotation}
						></textarea>
						{#if isControl}
							<div class="space-y-1" bind:this={evidenceListEl}>
								{#each newTypicalEvidence as _item, i (i)}
									<div class="flex items-center gap-1">
										<input
											type="text"
											class="evidence-item-input flex-1 text-xs px-2 py-1 border border-gray-200 rounded"
											placeholder={m.typicalEvidence()}
											bind:value={newTypicalEvidence[i]}
											onkeydown={(e) => handleEvidenceKeydown(e, i)}
										/>
										<button
											type="button"
											class="text-gray-400 hover:text-red-500"
											aria-label={m.remove()}
											onclick={() => removeEvidence(i)}
										>
											<i class="fa-solid fa-xmark"></i>
										</button>
									</div>
								{/each}
								<button
									type="button"
									class="text-xs text-blue-600 hover:text-blue-800"
									onclick={addEvidence}
								>
									<i class="fa-solid fa-plus mr-1"></i>{m.builderAddTypicalEvidence()}
								</button>
							</div>
						{/if}
						<div class="flex justify-end">
							<button
								type="button"
								class="text-xs px-2 py-1 rounded bg-blue-600 text-white disabled:opacity-50"
								disabled={!newRefId.trim()}
								onclick={createInline}
							>
								{m.create()}
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
