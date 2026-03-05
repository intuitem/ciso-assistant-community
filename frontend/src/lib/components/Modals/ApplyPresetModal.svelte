<script lang="ts">
	import { getModalStore } from './stores';
	import { m } from '$paraglide/messages';

	interface Props {
		parent: any;
		presetName: string;
		domains: { id: string; name: string }[];
		onApply: (data: {
			folder_name?: string;
			folder_id?: string;
			create_objects?: boolean;
		}) => Promise<{ ok: boolean; error?: string }>;
	}

	let { parent, presetName, domains, onApply }: Props = $props();

	const modalStore = getModalStore();

	let mode: 'new' | 'existing' = $state('new');
	let folderName: string = $state(presetName);
	let selectedFolderId: string = $state('');
	let createObjects: boolean = $state(true);
	let errorMessage: string = $state('');
	let submitting: boolean = $state(false);

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		errorMessage = '';
		submitting = true;

		try {
			let payload: { folder_name?: string; folder_id?: string; create_objects?: boolean };
			if (mode === 'new') {
				if (!folderName.trim()) return;
				payload = { folder_name: folderName.trim(), create_objects: createObjects };
			} else {
				if (!selectedFolderId) return;
				payload = { folder_id: selectedFolderId, create_objects: createObjects };
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
	<div class="card bg-surface-50 p-4 w-modal shadow-xl space-y-4">
		<header class="text-2xl font-bold">{$modalStore[0].title ?? m.applyPreset()}</header>
		<article class="whitespace-pre-line">{$modalStore[0].body ?? ''}</article>

		{#if errorMessage}
			<div class="p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
				{errorMessage}
			</div>
		{/if}

		<form class="space-y-4" onsubmit={handleSubmit}>
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
					<span class="text-sm font-medium" class:text-gray-400={domains.length === 0}>
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
				<label class="label">
					<span class="text-sm">{m.selectDomain()}</span>
					<select class="select" bind:value={selectedFolderId} required>
						<option value="" disabled>{m.selectDomain()}...</option>
						{#each domains as domain}
							<option value={domain.id}>{domain.name}</option>
						{/each}
					</select>
				</label>
			{/if}

			<!-- Create objects toggle -->
			<label
				class="flex items-start gap-3 cursor-pointer p-3 rounded-lg bg-gray-50 border border-gray-200"
			>
				<input type="checkbox" class="checkbox mt-0.5" bind:checked={createObjects} />
				<div>
					<span class="text-sm font-medium">{m.createUnderlyingObjects()}</span>
					<p class="text-xs text-gray-500 mt-0.5">{m.createUnderlyingObjectsHelp()}</p>
				</div>
			</label>

			<footer class="flex justify-end space-x-2">
				<button type="button" class="btn {parent.buttonNeutral}" onclick={parent.onClose}>
					{m.cancel()}
				</button>
				<button type="submit" class="btn {parent.buttonPositive}" disabled={submitting}>
					{#if submitting}
						<i class="fa-solid fa-spinner fa-spin mr-1"></i>
					{/if}
					{m.applyPreset()}
				</button>
			</footer>
		</form>
	</div>
{/if}
