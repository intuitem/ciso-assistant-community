<script lang="ts">
	import { getModalStore } from './stores';
	import { m } from '$paraglide/messages';
	import { page } from '$app/stores';
	import { onDestroy } from 'svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';

	interface Props {
		parent: any;
		presetName?: string;
		presets?: { id: string; name: string }[];
		domains: { id: string; name: string }[];
		onApply: (data: {
			preset_id?: string;
			folder_name?: string;
			folder_id?: string;
			create_objects?: boolean;
			apply_feature_flags?: boolean;
		}) => Promise<{ ok: boolean; error?: string }>;
	}

	let { parent, presetName = '', presets = [], domains, onApply }: Props = $props();

	const modalStore = getModalStore();

	const canChangeSettings = $derived(
		Object.hasOwn($page.data.user?.permissions ?? {}, 'change_globalsettings')
	);

	// When no preset is pre-selected (e.g. opened from the journeys list "Start a journey"
	// button), let the user pick which preset to apply.
	const showPresetPicker = $derived(presets.length > 0);

	let mode: 'new' | 'existing' = $state('new');
	let selectedPresetId: string = $state('');
	let folderName: string = $state(presetName);
	let selectedFolderId: string = $state('');
	let createObjects: boolean = $state(true);
	let applyFeatureFlags: boolean = $state(true);
	let errorMessage: string = $state('');
	let submitting: boolean = $state(false);

	// Standalone SPA form backing the hierarchical domain picker (FolderTreeSelect
	// requires a SuperForm); we mirror its value into selectedFolderId.
	const folderSchema = z.object({ folder: z.string() });
	const _form = superForm(defaults({ folder: '' }, zod(folderSchema)), {
		dataType: 'json',
		taintedMessage: false,
		validators: zod(folderSchema),
		SPA: true
	});
	const unsubscribeFolder = _form.form.subscribe((v) => {
		selectedFolderId = v.folder ?? '';
	});
	onDestroy(unsubscribeFolder);

	// Default the new-domain name to the chosen preset's name.
	$effect(() => {
		if (showPresetPicker && selectedPresetId) {
			const p = presets.find((x) => x.id === selectedPresetId);
			if (p) folderName = p.name;
		}
	});

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		errorMessage = '';
		submitting = true;

		try {
			let payload: {
				preset_id?: string;
				folder_name?: string;
				folder_id?: string;
				create_objects?: boolean;
				apply_feature_flags?: boolean;
			};
			if (mode === 'new') {
				if (!folderName.trim()) return;
				payload = {
					folder_name: folderName.trim(),
					create_objects: createObjects,
					apply_feature_flags: canChangeSettings && applyFeatureFlags
				};
			} else {
				if (!selectedFolderId) {
					errorMessage = m.selectDomain();
					return;
				}
				payload = {
					folder_id: selectedFolderId,
					create_objects: createObjects,
					apply_feature_flags: canChangeSettings && applyFeatureFlags
				};
			}
			// Only carry preset_id when the picker is in use, so we never clobber a
			// preset_id the caller already supplied (standard per-card apply).
			if (showPresetPicker && selectedPresetId) {
				payload.preset_id = selectedPresetId;
			}

			const result = await onApply(payload);
			if (result.ok) {
				modalStore.close();
			} else {
				errorMessage = result.error || m.error();
			}
		} catch {
			errorMessage = m.error();
		} finally {
			submitting = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div class="card bg-surface-50-950 p-4 w-modal shadow-xl space-y-4">
		<header class="text-2xl font-bold">{$modalStore[0].title ?? m.applyPreset()}</header>
		<article class="whitespace-pre-line">{$modalStore[0].body ?? ''}</article>

		{#if errorMessage}
			<div
				class="p-3 rounded-md bg-red-50 dark:bg-surface-800 border border-red-200 dark:border-red-900 text-sm text-red-700 dark:text-red-300"
			>
				{errorMessage}
			</div>
		{/if}

		<form class="space-y-4" onsubmit={handleSubmit}>
			<!-- Preset picker (only when no preset was pre-selected) -->
			{#if showPresetPicker}
				<label class="label">
					<span class="text-sm">{m.preset()}</span>
					<select
						class="select"
						bind:value={selectedPresetId}
						data-testid="apply-preset-select"
						required
					>
						<option value="" disabled>{m.preset()}...</option>
						{#each presets as preset}
							<option value={preset.id}>{preset.name}</option>
						{/each}
					</select>
				</label>
			{/if}

			<!-- Radio toggle -->
			<div class="flex gap-4">
				<label class="flex items-center gap-2 cursor-pointer">
					<input type="radio" name="mode" value="new" bind:group={mode} class="radio" />
					<span class="text-sm font-medium">{m.createNewDomain()}</span>
				</label>
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="radio"
						name="mode"
						value="existing"
						bind:group={mode}
						class="radio"
						disabled={domains.length === 0}
					/>
					<span class="text-sm font-medium" class:text-surface-500={domains.length === 0}>
						{m.useExistingDomain()}
					</span>
				</label>
			</div>

			<!-- Conditional input -->
			{#if mode === 'new'}
				<label class="label">
					<span class="text-sm">{m.domainName()}</span>
					<input
						type="text"
						class="input"
						bind:value={folderName}
						placeholder={presetName}
						required
					/>
				</label>
			{:else}
				<FolderTreeSelect form={_form} field="folder" label={m.selectDomain()} />
			{/if}

			<!-- Create objects toggle -->
			<label
				class="flex items-start gap-3 cursor-pointer p-3 rounded-lg bg-indigo-50 dark:bg-surface-800 border border-indigo-200 dark:border-indigo-900"
			>
				<input type="checkbox" class="checkbox mt-0.5" bind:checked={createObjects} />
				<div>
					<span class="text-sm font-medium flex items-center gap-1.5">
						<i class="fa-solid fa-cubes text-indigo-600 text-xs"></i>
						{m.createUnderlyingObjects()}
					</span>
					<p class="text-xs text-surface-600-400 mt-0.5">{m.createUnderlyingObjectsHelp()}</p>
				</div>
			</label>

			<!-- Apply feature flags toggle -->
			<label
				class="flex items-start gap-3 p-3 rounded-lg border {canChangeSettings
					? 'cursor-pointer bg-amber-50 dark:bg-surface-800 border-amber-200 dark:border-amber-900'
					: 'bg-surface-100-900 border-surface-200-800 opacity-60'}"
			>
				<input
					type="checkbox"
					class="checkbox mt-0.5"
					bind:checked={applyFeatureFlags}
					disabled={!canChangeSettings}
				/>
				<div>
					<span class="text-sm font-medium flex items-center gap-1.5">
						<i class="fa-solid fa-sliders text-amber-600 text-xs"></i>
						{m.applyFeatureFlags()}
					</span>
					<p class="text-xs text-surface-600-400 mt-0.5">{m.applyFeatureFlagsHelp()}</p>
					{#if !canChangeSettings}
						<p class="text-xs text-amber-600 mt-1">
							<i class="fa-solid fa-lock text-[10px] mr-1"></i>
							{m.applyFeatureFlagsNoPermission()}
						</p>
					{/if}
				</div>
			</label>

			<footer class="flex justify-end space-x-2">
				<button type="button" class="btn {parent.buttonNeutral}" onclick={parent.onClose}>
					{m.cancel()}
				</button>
				<button
					type="submit"
					class="btn {parent.buttonPositive}"
					data-testid="apply-preset-confirm-btn"
					disabled={submitting}
				>
					{#if submitting}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{/if}
					{m.applyPreset()}
				</button>
			</footer>
		</form>
	</div>
{/if}
