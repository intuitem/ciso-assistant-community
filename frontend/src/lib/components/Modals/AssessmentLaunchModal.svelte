<script lang="ts">
	import { goto } from '$app/navigation';
	import { deserialize } from '$app/forms';
	import { onDestroy } from 'svelte';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';

	interface Props {
		parent: any;
		item: string;
		showName?: boolean;
		defaultName?: string;
		showDomain?: boolean;
	}

	let { item, showName = false, defaultName = '', showDomain = false }: Props = $props();
	const modalStore: ModalStore = getModalStore();

	let name = $state(defaultName);
	let folder = $state('');
	let busy = $state(false);
	let error = $state('');

	// Standalone SPA form backing the hierarchical domain picker (FolderTreeSelect requires
	// a SuperForm); we mirror its value into `folder`. Using field="folder" surfaces the
	// personal "My space" option, and the write-perm filter limits the tree to domains where
	// the user may actually create the assessment.
	const folderSchema = z.object({ folder: z.string() });
	const _form = superForm(defaults({ folder: '' }, zod(folderSchema)), {
		dataType: 'json',
		taintedMessage: false,
		validators: zod(folderSchema),
		SPA: true
	});
	const unsubscribeFolder = _form.form.subscribe((v) => {
		folder = v.folder ?? '';
	});
	onDestroy(unsubscribeFolder);

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
			<FolderTreeSelect
				form={_form}
				field="folder"
				label={m.domain()}
				writePermission="add_complianceassessment"
			/>
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
