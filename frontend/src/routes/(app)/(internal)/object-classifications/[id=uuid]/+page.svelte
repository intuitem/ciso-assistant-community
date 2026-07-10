<script lang="ts">
	import { m } from '$paraglide/messages';
	import { invalidateAll } from '$app/navigation';
	import { isDark } from '$lib/utils/helpers';
	import { getToastStore } from '$lib/components/Toast/stores';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';

	let { data } = $props();
	let scheme = $derived(data.scheme);
	let levels = $derived([...(scheme.levels ?? [])].sort((a: any, b: any) => a.rank - b.rank));
	let busy = $state(false);

	const toastStore = getToastStore();
	const modalStore: ModalStore = getModalStore();
	function notifyError(msg: string) {
		toastStore.trigger({ message: msg, preset: 'error' });
	}

	let newAbbr = $state('');
	let newName = $state('');
	let newColor = $state('#64748b');

	let editingId = $state<string | null>(null);
	let editAbbr = $state('');
	let editName = $state('');
	let editColor = $state('#64748b');

	const base = () => `/object-classifications/${scheme.id}`;

	async function op(method: string, body: any, query = '') {
		busy = true;
		try {
			const res = await fetch(base() + query, {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: body ? JSON.stringify(body) : undefined
			});
			if (res.ok) await invalidateAll();
			else {
				const d = await res.json().catch(() => null);
				notifyError(d?.detail || d?.error || d?.abbreviation || m.error());
			}
			return res.ok;
		} finally {
			busy = false;
		}
	}

	async function addLevel() {
		if (!newAbbr.trim()) return;
		const ok = await op('POST', {
			abbreviation: newAbbr.trim(),
			name: newName.trim() || newAbbr.trim().toLowerCase(),
			hexcolor: newColor,
			rank: levels.length,
			is_visible: true
		});
		if (ok) {
			newAbbr = '';
			newName = '';
			newColor = '#64748b';
		}
	}

	const toggleVisible = (l: any) => op('PATCH', { id: l.id, is_visible: !l.is_visible });

	const del = (l: any) => {
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal,
			props: { bodyComponent: undefined }
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.delete(),
			body: m.deleteConfirm(),
			response: (confirmed: boolean) => {
				if (confirmed) op('DELETE', null, `?level=${l.id}`);
			}
		};
		modalStore.trigger(modal);
	};

	async function move(l: any, dir: number) {
		const i = levels.findIndex((x: any) => x.id === l.id);
		const j = i + dir;
		if (j < 0 || j >= levels.length) return;
		const other = levels[j];
		busy = true;
		try {
			const results = await Promise.all([
				fetch(base(), {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ id: l.id, rank: other.rank })
				}),
				fetch(base(), {
					method: 'PATCH',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ id: other.id, rank: l.rank })
				})
			]);
			if (results.some((r) => !r.ok)) notifyError(m.error());
			await invalidateAll();
		} catch {
			notifyError(m.error());
			await invalidateAll();
		} finally {
			busy = false;
		}
	}

	function startEdit(l: any) {
		editingId = l.id;
		editAbbr = l.abbreviation ?? '';
		editName = l.name ?? '';
		editColor = l.hexcolor || '#64748b';
	}
	async function saveEdit(l: any) {
		const ok = await op('PATCH', {
			id: l.id,
			abbreviation: editAbbr.trim(),
			name: editName.trim(),
			hexcolor: editColor
		});
		if (ok) editingId = null;
	}
</script>

<div class="mx-auto max-w-3xl space-y-6 p-4 sm:p-6">
	<a
		href="/object-classifications"
		class="inline-flex items-center gap-1.5 text-sm text-surface-500 transition-colors hover:text-primary-500"
	>
		<i class="fa-solid fa-arrow-left"></i>{m.objectClassifications()}
	</a>

	<!-- Scheme header -->
	<header
		class="relative overflow-hidden rounded-xl border border-surface-200-800 bg-surface-50-950 p-6 pl-7"
	>
		<span class="absolute inset-y-0 left-0 w-1.5 bg-primary-500"></span>
		<div class="flex items-start justify-between gap-3">
			<div class="flex items-center gap-4">
				<div
					class="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-primary-500/10 text-xl text-primary-500 ring-1 ring-primary-500/20"
				>
					<i class="fa-solid fa-shield-halved"></i>
				</div>
				<div>
					<h1 class="text-2xl font-bold leading-tight tracking-tight">{scheme.name}</h1>
					<div class="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-surface-500">
						{#if scheme.ref_id}<span class="font-mono">{scheme.ref_id}</span>{/if}
						{#if scheme.builtin}
							<span class="rounded bg-surface-200-800 px-1.5 py-0.5">{m.builtin()}</span>
						{/if}
						{#if !scheme.is_visible}
							<span class="rounded bg-surface-200-800 px-1.5 py-0.5" title={m.isVisible()}>
								<i class="fa-solid fa-eye-slash"></i>
							</span>
						{/if}
					</div>
				</div>
			</div>
		</div>
	</header>

	<!-- Levels -->
	<div class="rounded-xl border border-surface-200-800 bg-surface-50-950 p-4 sm:p-6">
		<h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-surface-600-400">
			{m.classificationLevels()}
		</h2>
		<ul class="space-y-1.5">
			{#each levels as l, i (l.id)}
				<li
					class="flex items-center gap-3 rounded-lg border border-surface-200-800 bg-surface-100-900/50 px-3 py-2 {l.is_visible
						? ''
						: 'opacity-50'}"
				>
					<div class="flex flex-col text-surface-400">
						<button
							class="hover:text-primary-500 disabled:opacity-30"
							disabled={busy || i === 0}
							onclick={() => move(l, -1)}
							aria-label={m.moveUp()}><i class="fa-solid fa-chevron-up text-xs"></i></button
						>
						<button
							class="hover:text-primary-500 disabled:opacity-30"
							disabled={busy || i === levels.length - 1}
							onclick={() => move(l, 1)}
							aria-label={m.moveDown()}><i class="fa-solid fa-chevron-down text-xs"></i></button
						>
					</div>
					<span class="w-5 text-center text-xs tabular-nums text-surface-400">{l.rank}</span>

					{#if editingId === l.id}
						<input type="color" bind:value={editColor} class="h-8 w-10 rounded" />
						<input bind:value={editAbbr} class="input w-28" placeholder={m.abbreviation()} />
						<input bind:value={editName} class="input flex-1" placeholder={m.name()} />
						<button
							class="btn btn-sm variant-filled-primary"
							disabled={busy}
							onclick={() => saveEdit(l)}>{m.save()}</button
						>
						<button class="btn btn-sm variant-soft" onclick={() => (editingId = null)}
							>{m.cancel()}</button
						>
					{:else}
						<span
							class="inline-flex min-w-24 items-center justify-center rounded px-2 py-1 text-xs font-semibold uppercase ring-1 ring-black/10"
							style="background:{l.hexcolor || '#64748b'};color:{isDark(l.hexcolor)
								? '#fff'
								: '#0f172a'}">{l.abbreviation || l.name}</span
						>
						<span class="flex-1 truncate text-sm">{l.label ?? l.name}</span>
						<button
							class="text-surface-400 hover:text-primary-500"
							disabled={busy}
							title={m.isVisible()}
							onclick={() => toggleVisible(l)}
						>
							<i class="fa-solid {l.is_visible ? 'fa-eye' : 'fa-eye-slash'}"></i>
						</button>
						{#if !l.builtin}
							<button
								class="text-surface-400 hover:text-primary-500"
								disabled={busy}
								onclick={() => startEdit(l)}
								aria-label={m.edit()}><i class="fa-solid fa-pen"></i></button
							>
							<button
								class="text-surface-400 hover:text-error-500"
								disabled={busy}
								onclick={() => del(l)}
								aria-label={m.delete()}><i class="fa-solid fa-trash"></i></button
							>
						{:else}
							<span class="w-4 text-center text-[10px] text-surface-400" title={m.builtin()}>
								<i class="fa-solid fa-lock"></i>
							</span>
						{/if}
					{/if}
				</li>
			{/each}
		</ul>

		<!-- Add level -->
		<div class="mt-4 flex flex-wrap items-center gap-2 border-t border-surface-200-800 pt-4">
			<input type="color" bind:value={newColor} class="h-9 w-11 rounded" />
			<input bind:value={newAbbr} class="input w-32" placeholder={m.abbreviation()} />
			<input bind:value={newName} class="input min-w-40 flex-1" placeholder={m.name()} />
			<button
				class="btn variant-filled-primary"
				disabled={busy || !newAbbr.trim()}
				onclick={addLevel}
			>
				<i class="fa-solid fa-plus mr-2"></i>{m.addLevel()}
			</button>
		</div>
	</div>
</div>
