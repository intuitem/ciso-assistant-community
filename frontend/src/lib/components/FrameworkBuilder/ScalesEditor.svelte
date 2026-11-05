<script lang="ts">
	import {
		getTranslation,
		ruleIdFromLabel,
		withTranslation,
		type Scale,
		type ScaleLevel
	} from './builder-state';
	import ConfirmAction from './ConfirmAction.svelte';
	import { SECTION_ICON, SECTION_TITLE } from './section-style';
	import { m } from '#paraglide/messages.js';

	// The form's scales: ordered levels choice questions share (`config.scale`), and
	// ratings measure. A level's id names its choices, so it is set once, from
	// its first label, and never renamed: answers already given keep pointing at it.
	interface Props {
		scales: Scale[];
		/** Scales questions or matrices use: not deletable. */
		used: string[];
		activeLanguage?: string | null;
		onupdate: (scales: Scale[]) => void;
	}

	let { scales, used, activeLanguage = null, onupdate }: Props = $props();

	let local: Scale[] = $state([]);
	$effect(() => {
		local = scales.map((s) => ({ ...s, levels: s.levels.map((l) => ({ ...l })) }));
	});

	function persist() {
		onupdate(local.map((s) => ({ ...s, levels: s.levels.map((l) => ({ ...l })) })));
	}

	function addScale() {
		local = [...local, { ref_id: '', label: '', levels: [] }];
		persist();
	}

	function setScaleLabel(index: number, label: string) {
		const scale = local[index];
		if (!scale.ref_id && label.trim()) {
			scale.ref_id = ruleIdFromLabel(
				label,
				local.filter((_, i) => i !== index).map((s) => s.ref_id)
			);
		}
		scale.label = label;
		persist();
	}

	function addLevel(index: number) {
		local[index].levels = [...local[index].levels, { ref_id: '', label: '' }];
		persist();
	}

	function setLevel(index: number, li: number, patch: Partial<ScaleLevel>) {
		const level = local[index].levels[li];
		if (!level.ref_id && patch.label?.trim()) {
			level.ref_id = ruleIdFromLabel(
				patch.label,
				local[index].levels.filter((_, i) => i !== li).map((l) => l.ref_id)
			);
		}
		Object.assign(level, patch);
		if (!level.color) delete level.color;
		if (!level.description) delete level.description;
		persist();
	}

	function moveLevel(index: number, li: number, to: number) {
		const levels = [...local[index].levels];
		const [moved] = levels.splice(li, 1);
		levels.splice(to, 0, moved);
		local[index].levels = levels;
		persist();
	}
</script>

<div class="space-y-3" data-testid="scales-editor">
	<div>
		<h3 class={SECTION_TITLE}>
			<i class="fa-solid fa-ruler-horizontal {SECTION_ICON}"></i>{m.builderScales()}
		</h3>
		<p class="text-xs text-surface-500">{m.builderScalesHelp()}</p>
	</div>

	{#each local as scale, index (index)}
		<div class="rounded-lg border border-surface-200-800 p-3 space-y-2">
			<div class="flex items-center gap-2">
				<input
					class="input flex-1 text-sm py-1"
					value={scale.label ?? ''}
					placeholder={m.builderScaleLabel()}
					onblur={(e) => setScaleLabel(index, e.currentTarget.value)}
				/>
				{#if scale.ref_id}<code class="text-xs text-surface-500">{scale.ref_id}</code>{/if}
				{#if used.includes(scale.ref_id)}
					<i class="fa-solid fa-lock text-xs text-surface-400" title={m.builderScaleInUse()}></i>
				{:else}
					<ConfirmAction
						onconfirm={() => {
							local = local.filter((_, i) => i !== index);
							persist();
						}}
					/>
				{/if}
			</div>
			{#if activeLanguage}
				<input
					class="input w-full text-sm py-1 border-blue-100"
					value={getTranslation(scale.translations, activeLanguage, 'label')}
					placeholder={m.builderCelLabelTranslate({ lang: activeLanguage.toUpperCase() })}
					onblur={(e) => {
						scale.translations = withTranslation(
							scale.translations,
							activeLanguage!,
							'label',
							e.currentTarget.value
						);
						persist();
					}}
				/>
			{/if}

			<ol class="space-y-1">
				{#each scale.levels as level, li (li)}
					<li class="flex flex-wrap items-center gap-2 text-sm">
						<span class="w-5 text-right text-xs text-surface-500">{li + 1}</span>
						<input
							type="color"
							class="h-7 w-8 cursor-pointer rounded border border-surface-200-800"
							value={level.color || '#ffffff'}
							onchange={(e) => setLevel(index, li, { color: e.currentTarget.value })}
						/>
						<input
							class="input w-40 text-sm py-1"
							value={level.label}
							placeholder={m.builderLevelLabel()}
							onblur={(e) => setLevel(index, li, { label: e.currentTarget.value })}
						/>
						<input
							class="input flex-1 min-w-48 text-sm py-1"
							value={level.description ?? ''}
							placeholder={m.builderLevelDescription()}
							onblur={(e) => setLevel(index, li, { description: e.currentTarget.value })}
						/>
						{#if activeLanguage}
							{@const lang = activeLanguage}
							<input
								class="input w-40 text-sm py-1 border-blue-100"
								value={getTranslation(level.translations, lang, 'label')}
								placeholder="{m.builderLevelLabel()} ({lang.toUpperCase()})"
								onblur={(e) => {
									level.translations = withTranslation(
										level.translations,
										lang,
										'label',
										e.currentTarget.value
									);
									persist();
								}}
							/>
							<input
								class="input flex-1 min-w-48 text-sm py-1 border-blue-100"
								value={getTranslation(level.translations, lang, 'description')}
								placeholder="{m.builderLevelDescription()} ({lang.toUpperCase()})"
								onblur={(e) => {
									level.translations = withTranslation(
										level.translations,
										lang,
										'description',
										e.currentTarget.value
									);
									persist();
								}}
							/>
						{/if}
						<button
							type="button"
							class="text-xs text-surface-500 disabled:opacity-30"
							disabled={li === 0}
							aria-label="↑"
							onclick={() => moveLevel(index, li, li - 1)}
							><i class="fa-solid fa-arrow-up"></i></button
						>
						<button
							type="button"
							class="text-xs text-surface-500 disabled:opacity-30"
							disabled={li === scale.levels.length - 1}
							aria-label="↓"
							onclick={() => moveLevel(index, li, li + 1)}
							><i class="fa-solid fa-arrow-down"></i></button
						>
						<ConfirmAction
							onconfirm={() => {
								scale.levels = scale.levels.filter((_, i) => i !== li);
								persist();
							}}
						/>
					</li>
				{/each}
			</ol>
			<button type="button" class="btn btn-sm preset-tonal" onclick={() => addLevel(index)}>
				<i class="fa-solid fa-plus mr-1"></i>{m.builderAddLevel()}
			</button>
		</div>
	{/each}

	<button type="button" class="btn btn-sm preset-tonal-primary" onclick={addScale}>
		<i class="fa-solid fa-plus mr-1"></i>{m.builderAddScale()}
	</button>
</div>
