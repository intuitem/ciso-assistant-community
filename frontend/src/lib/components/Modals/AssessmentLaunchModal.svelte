<script lang="ts">
	import { goto } from '$app/navigation';
	import { deserialize } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';

	interface Props {
		parent: any;
		item: string;
		showName?: boolean;
		defaultName?: string;
		showDomain?: boolean;
		domains?: { id: string; name: string }[];
		personalFoldersEnabled?: boolean;
	}

	let {
		item,
		showName = false,
		defaultName = '',
		showDomain = false,
		domains = [],
		personalFoldersEnabled = false
	}: Props = $props();
	const modalStore: ModalStore = getModalStore();

	let name = $state(defaultName);
	let folder = $state('');
	let busy = $state(false);
	let error = $state('');

	const ready = $derived((!showDomain || !!folder) && (!showName || !!name.trim()));

	async function launch() {
		if (!ready || busy) return;
		busy = true;
		error = '';
		try {
			const body = new FormData();
			body.append('item', item);
			if (showDomain) body.append('folder', folder);
			if (showName) body.append('name', name.trim());
			const res = await fetch('?/launchAssessment', { method: 'POST', body });
			const result: any = deserialize(await res.text());
			if (result.type === 'success' && result.data?.redirect) {
				modalStore.close();
				await goto(result.data.redirect);
			} else {
				error = result.data?.error || m.assessmentLaunchFailed();
			}
		} catch {
			error = m.assessmentLaunchFailed();
		} finally {
			busy = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div class="card bg-surface-50-950 w-modal space-y-4 p-4 shadow-xl">
		<header class="text-2xl font-bold">{m.startQuestionnaire()}</header>
		{#if showName}
			<label class="block space-y-1">
				<span class="text-sm text-surface-600-400">{m.name()}</span>
				<input bind:value={name} class="input rounded-md" placeholder={defaultName} />
			</label>
		{/if}
		{#if showDomain}
			<label class="block space-y-1">
				<span class="text-sm text-surface-600-400">{m.domain()}</span>
				<select bind:value={folder} class="select rounded-md">
					<option value="">—</option>
					{#if personalFoldersEnabled}<option value="__personal__">{m.mySpace()}</option>{/if}
					{#each domains as d}<option value={d.id}>{d.name}</option>{/each}
				</select>
			</label>
		{/if}
		{#if error}<p class="text-sm text-error-500">{error}</p>{/if}
		<footer class="flex justify-end gap-2">
			<button class="btn preset-tonal" onclick={() => modalStore.close()}>{m.cancel()}</button>
			<button class="btn preset-filled-primary-500" disabled={!ready || busy} onclick={launch}
				>{m.start()}</button
			>
		</footer>
	</div>
{/if}
