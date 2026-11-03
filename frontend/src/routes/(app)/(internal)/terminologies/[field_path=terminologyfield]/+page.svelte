<script lang="ts">
	import { deserialize } from '$app/forms';
	import { refreshAll } from '$app/navigation';
	import { page } from '$app/state';
	import TerminologyBadge from '#lib/components/TerminologyBadge.svelte';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import { canPerformAction } from '#lib/utils/access-control.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import type { PageData } from './$types';

	interface Terminology {
		id: string;
		name: string;
		translated_name?: string;
		translations?: Record<string, unknown> | null;
		hexcolor: string;
		order: number;
		is_visible: boolean;
		builtin: boolean;
	}

	interface ApiError {
		error?: string;
		detail?: string;
		name?: string[];
		hexcolor?: string[];
		non_field_errors?: string[];
	}

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const toastStore = getToastStore();

	let terminologies: Terminology[] = $derived([...(data.terminologies as Terminology[])]);

	const rootFolderId = $derived(page.data.user?.root_folder_id);
	const can = (action: 'add' | 'change' | 'delete') =>
		canPerformAction({
			user: page.data.user,
			action,
			model: 'terminology',
			domain: rootFolderId
		});
	const canEdit = $derived(can('change'));
	const canAdd = $derived(can('add'));
	const canDelete = $derived(can('delete'));

	let busy = $state(false);
	let newName = $state('');
	let newColor = $state('#dbeafe');
	let dragIndex: number | null = $state(null);

	// Colours come from the database and reach inline styles: only bare hex gets through.
	const HEX = /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/;
	const FALLBACK = '#94a3b8';
	const colorOf = (t: Terminology) => (HEX.test(t.hexcolor ?? '') ? t.hexcolor : FALLBACK);
	const labelOf = (t: Terminology) =>
		t.translations && Object.keys(t.translations).length
			? (t.translated_name ?? t.name)
			: t.builtin
				? safeTranslate(t.name)
				: t.name;

	async function callAction(name: string, fields: Record<string, string>): Promise<boolean> {
		busy = true;
		const body = new FormData();
		for (const [key, value] of Object.entries(fields)) body.append(key, value);
		try {
			const res = await fetch(`?/${name}`, {
				method: 'POST',
				body,
				headers: { 'x-sveltekit-action': 'true' }
			});
			const result = deserialize(await res.text());
			if (result.type !== 'success') {
				const detail =
					result.type === 'failure' ? (result.data?.error as ApiError | undefined) : undefined;
				const message =
					detail?.error ??
					detail?.detail ??
					detail?.name?.[0] ??
					detail?.hexcolor?.[0] ??
					detail?.non_field_errors?.[0] ??
					undefined;
				toastStore.trigger({
					message: message ? safeTranslate(String(message)) : m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return false;
			}
			return true;
		} finally {
			await refreshAll();
			busy = false;
		}
	}

	function update(t: Terminology, payload: Partial<Terminology>) {
		return callAction('update', { id: t.id, payload: JSON.stringify(payload) });
	}

	function move(from: number, to: number) {
		if (to < 0 || to >= terminologies.length || from === to) return;
		const next = [...terminologies];
		const [moved] = next.splice(from, 1);
		next.splice(to, 0, moved);
		terminologies = next;
		callAction('reorder', { ids: JSON.stringify(terminologies.map((t) => t.id)) });
	}

	function onDrop(index: number) {
		if (dragIndex !== null) move(dragIndex, index);
		dragIndex = null;
	}

	async function addValue(event: SubmitEvent) {
		event.preventDefault();
		if (!newName.trim()) return;
		if (await callAction('create', { name: newName.trim(), hexcolor: newColor })) {
			newName = '';
		}
	}
</script>

<div class="bg-surface-50-950 shadow-sm flex flex-col">
	<header
		class="flex flex-wrap items-start justify-between gap-4 px-6 pt-6 pb-5 border-b border-surface-200-800"
	>
		<div class="flex flex-col gap-1 max-w-2xl">
			<h1 class="text-2xl font-semibold tracking-tight text-surface-950-50">{data.title}</h1>
			<code class="text-xs text-surface-500">{data.fieldPath}</code>
			<p class="mt-1 text-sm text-surface-600-400">{m.terminologyFieldDescription()}</p>
		</div>
		<a
			href="/terminologies"
			class="text-sm text-primary-800-200 hover:text-primary-500 whitespace-nowrap pt-1"
		>
			<i class="fa-solid fa-arrow-left mr-2"></i>{m.terminologies()}
		</a>
	</header>

	<section class="p-6 max-w-4xl" aria-label={data.title}>
		{#if terminologies.length === 0}
			<p class="mb-3 text-sm text-surface-500">{m.noTerminologyValues()}</p>
		{/if}
		<ol class="flex flex-col gap-2" data-testid="terminology-values">
			{#each terminologies as terminology, index (terminology.id)}
				{@const color = colorOf(terminology)}
				<li
					class="group {dragIndex === index ? 'opacity-40' : ''}"
					draggable={canEdit && !busy}
					ondragstart={() => (dragIndex = index)}
					ondragend={() => (dragIndex = null)}
					ondragover={(e) => e.preventDefault()}
					ondrop={() => onDrop(index)}
					data-testid="terminology-value-row"
				>
					<div
						class="flex flex-wrap items-center gap-3 rounded-xl border border-l-4 bg-surface-50-950 py-2 pl-3 pr-3 transition-shadow group-hover:shadow-md {terminology.is_visible
							? 'border-surface-200-800'
							: 'border-dashed border-surface-300-700 opacity-70'}"
						style="border-left-color: {color}"
					>
						<span class="w-6 text-right text-xs tabular-nums text-surface-500">{index + 1}</span>

						{#if canEdit}
							<div
								class="flex items-center gap-0.5 opacity-40 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
							>
								<span class="cursor-grab px-1 text-surface-400" aria-hidden="true">
									<i class="fa-solid fa-grip-vertical"></i>
								</span>
								<div class="flex flex-col">
									<button
										type="button"
										class="btn-icon btn-icon-sm h-5"
										aria-label={m.moveUp()}
										disabled={busy || index === 0}
										onclick={() => move(index, index - 1)}
									>
										<i class="fa-solid fa-chevron-up text-[10px]"></i>
									</button>
									<button
										type="button"
										class="btn-icon btn-icon-sm h-5"
										aria-label={m.moveDown()}
										disabled={busy || index === terminologies.length - 1}
										onclick={() => move(index, index + 1)}
									>
										<i class="fa-solid fa-chevron-down text-[10px]"></i>
									</button>
								</div>
							</div>

							<!-- The swatch is the colour picker: the native input sits on top of it. -->
							<label
								class="relative size-8 shrink-0 cursor-pointer rounded-full ring-2 ring-offset-2 ring-offset-surface-50-950 ring-transparent transition hover:ring-surface-300-700 focus-within:ring-primary-500"
								style="background: {color}"
							>
								<input
									type="color"
									class="absolute inset-0 size-full cursor-pointer opacity-0"
									value={color}
									aria-label={m.color()}
									disabled={busy}
									onchange={(e) => update(terminology, { hexcolor: e.currentTarget.value })}
								/>
							</label>
						{/if}

						{#if canEdit && !terminology.builtin}
							<input
								class="min-w-40 flex-1 rounded-md border border-transparent bg-transparent px-2 py-1 text-base font-medium text-surface-950-50 outline-none transition hover:border-surface-300-700 focus:border-primary-500 focus:bg-surface-100-900"
								value={terminology.name}
								aria-label={m.name()}
								disabled={busy}
								onchange={(e) => {
									const value = e.currentTarget.value.trim();
									if (value && value !== terminology.name) update(terminology, { name: value });
								}}
							/>
						{:else}
							<div class="flex flex-1 items-center gap-2 py-1">
								<TerminologyBadge
									name={labelOf(terminology)}
									hexcolor={terminology.hexcolor}
									class="text-sm"
								/>
								{#if terminology.builtin}
									<span class="text-xs text-surface-500">{m.builtin()}</span>
								{/if}
							</div>
						{/if}

						{#if canEdit}
							<a
								href={`/terminologies/${terminology.id}/edit?next=${encodeURIComponent(page.url.pathname)}`}
								class="btn-icon btn-icon-sm text-surface-500"
								aria-label={m.edit()}
								title={m.edit()}
							>
								<i class="fa-solid fa-pen-to-square"></i>
							</a>
							<button
								type="button"
								class="btn-icon btn-icon-sm {terminology.is_visible
									? 'text-surface-500'
									: 'text-warning-600-400'}"
								aria-pressed={!terminology.is_visible}
								aria-label={terminology.is_visible ? m.hide() : m.show()}
								title={terminology.is_visible ? m.visible() : m.hidden()}
								disabled={busy}
								onclick={() => update(terminology, { is_visible: !terminology.is_visible })}
							>
								<i class="fa-solid {terminology.is_visible ? 'fa-eye' : 'fa-eye-slash'}"></i>
							</button>
						{:else if !terminology.is_visible}
							<span class="badge preset-tonal text-xs">{m.hidden()}</span>
						{/if}

						{#if canDelete && !terminology.builtin}
							<button
								type="button"
								class="btn-icon btn-icon-sm text-error-500"
								aria-label={m.delete()}
								title={m.delete()}
								disabled={busy}
								onclick={() => callAction('remove', { id: terminology.id })}
							>
								<i class="fa-solid fa-trash"></i>
							</button>
						{/if}
					</div>
				</li>
			{/each}

			{#if canAdd}
				<li>
					<form
						class="flex flex-wrap items-center gap-3 rounded-xl border-2 border-dashed border-surface-300-700 py-2 pl-4 pr-2 transition-colors focus-within:border-primary-500"
						onsubmit={addValue}
						data-testid="add-terminology-form"
					>
						<label
							class="relative size-8 shrink-0 cursor-pointer rounded-full ring-2 ring-offset-2 ring-offset-surface-50-950 ring-transparent hover:ring-surface-300-700 focus-within:ring-primary-500"
							style="background: {HEX.test(newColor) ? newColor : FALLBACK}"
						>
							<input
								type="color"
								class="absolute inset-0 size-full cursor-pointer opacity-0"
								bind:value={newColor}
								aria-label={m.color()}
								disabled={busy}
							/>
						</label>
						<input
							class="min-w-40 flex-1 rounded-md border border-transparent bg-transparent px-2 py-1 text-base outline-none placeholder:text-surface-400 focus:border-primary-500"
							bind:value={newName}
							placeholder={m.addTerminologyValue()}
							aria-label={m.name()}
							disabled={busy}
							required
						/>
						<button
							class="btn btn-sm preset-filled-primary-500"
							type="submit"
							disabled={busy || !newName.trim()}
						>
							<i class="fa-solid fa-plus mr-1.5"></i>{m.addTerminologyValue()}
						</button>
					</form>
				</li>
			{/if}
		</ol>
	</section>
</div>
