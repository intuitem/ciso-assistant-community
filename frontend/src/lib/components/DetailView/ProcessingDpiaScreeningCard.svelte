<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { canPerformActionOnObject } from '$lib/utils/access-control';
	import { formatDate } from '$lib/utils/datetime';
	import { safeTranslate } from '$lib/utils/i18n';
	import { getLocale } from '$paraglide/runtime';
	import { m } from '$paraglide/messages';

	interface Props {
		processing: Record<string, any>;
	}

	let { processing }: Props = $props();

	const toastStore = getToastStore();
	const screening = $derived(processing.dpia_screening);

	const canChange = $derived(
		canPerformActionOnObject({
			user: page.data.user,
			action: 'change',
			model: 'processing',
			object: processing
		})
	);

	// Forms the viewer may fill in-house, else publications they may file,
	// that screen this processing.
	type Option = { kind: 'form' | 'publication'; id: string; name: string };
	let screenings: Option[] | null = $state(null);
	// A failed lookup is not "no form loaded": say so instead.
	let loadFailed = $state(false);
	// Which list of forms is open, when there is more than one to choose from.
	let choosing: 'screening' | 'dpia' | null = $state(null);
	$effect(() => {
		// Aborted when the processing changes, so a late answer cannot land on another one.
		const controller = new AbortController();
		loadFailed = false;
		fetch(`/processings/${processing.id}/dpia-screening`, { signal: controller.signal })
			.then((res) => {
				if (!res.ok) throw new Error(String(res.status));
				return res.json();
			})
			.then((rows) => (screenings = Array.isArray(rows) ? rows : []))
			.catch(() => {
				if (controller.signal.aborted) return;
				screenings = null;
				loadFailed = true;
			});
		return () => controller.abort();
	});

	// The DPIA forms the viewer may start on this processing, and its latest DPIA:
	// the card's next step is to start one or to follow it.
	let dpiaForms: Option[] | null = $state(null);
	let dpia: Record<string, any> | null | undefined = $state(undefined);
	$effect(() => {
		const controller = new AbortController();
		const { signal } = controller;
		fetch(`/processings/${processing.id}/dpia-screening?target=processing.dpia`, { signal })
			.then((res) => (res.ok ? res.json() : []))
			.then((rows) => (dpiaForms = Array.isArray(rows) ? rows : []))
			.catch(() => {
				if (!signal.aborted) dpiaForms = [];
			});
		const query = new URLSearchParams({
			target: 'processing.dpia',
			subject_object_id: processing.id,
			ordering: '-updated_at'
		});
		fetch(`/quick-form-responses?${query}`, { signal })
			.then((res) => (res.ok ? res.json() : null))
			// A rejected DPIA is no DPIA: the card offers to start another.
			.then(
				(body) =>
					(dpia =
						body?.results?.find(
							(r: Record<string, any>) => !(r.status === 'closed' && r.resolution === 'rejected')
						) ?? null)
			)
			.catch(() => {
				if (!signal.aborted) dpia = null;
			});
		return () => controller.abort();
	});

	function startDpia() {
		if (dpiaForms?.length === 1) screen(dpiaForms[0]);
		else choosing = choosing === 'dpia' ? null : 'dpia';
	}

	function startScreening() {
		if (screenings?.length === 1) screen(screenings[0]);
		else choosing = choosing === 'screening' ? null : 'screening';
	}

	// One start at a time: a double click must not open two drafts.
	let starting = $state(false);

	async function screen(option: Option) {
		if (starting) return;
		starting = true;
		try {
			const res = await fetch(`/processings/${processing.id}/dpia-screening`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ kind: option.kind, id: option.id })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok || !body.redirect) {
				toastStore.trigger({
					message: body.error ? safeTranslate(body.error) : m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			await goto(body.redirect);
		} catch {
			toastStore.trigger({ message: m.anErrorOccurred(), background: 'preset-filled-error-500' });
		} finally {
			starting = false;
		}
	}

	// One sentence per source: who or what set the verdict, and when.
	function verdictOrigin(p: Record<string, any>): string {
		const date = p.dpia_required_set_at
			? formatDate(new Date(p.dpia_required_set_at), false, getLocale())
			: '';
		if (p.dpia_required_source === 'manual')
			return date ? m.dpiaSetManuallyOn({ date }) : m.dpiaSourceManual();
		if (p.dpia_required_source === 'override')
			return date ? m.dpiaAdjustedOn({ date }) : m.dpiaSourceOverride();
		if (p.dpia_required_source === 'assessment' && date) return m.dpiaScreenedOn({ date });
		return '';
	}

	let editing = $state(false);
	let saving = $state(false);
	let selected = $state('false');
	let note = $state('');

	function startEditing() {
		selected = String(!!processing.dpia_required);
		note = '';
		choosing = null;
		editing = true;
	}

	async function save() {
		saving = true;
		try {
			const res = await fetch(`/processings/${processing.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ dpia_required: selected === 'true', dpia_required_note: note })
			});
			if (!res.ok) {
				toastStore.trigger({
					message: m.anErrorOccurred(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			editing = false;
			await invalidateAll();
		} catch {
			toastStore.trigger({ message: m.anErrorOccurred(), background: 'preset-filled-error-500' });
		} finally {
			saving = false;
		}
	}
</script>

<div
	class="card p-4 bg-surface-50-950 border border-surface-200-800 flex flex-col gap-3"
	data-testid="dpia-screening-card"
>
	<div class="flex items-center justify-between">
		<h3 class="font-semibold text-surface-950-50">
			<i class="fa-solid fa-clipboard-question mr-2"></i>{m.dpiaScreening()}
		</h3>
		{#if !editing}
			<div class="flex flex-wrap justify-end gap-2">
				{#if screenings?.length}
					<button
						type="button"
						class="btn btn-sm {processing.dpia_required_source
							? 'preset-tonal-primary'
							: 'preset-filled-primary-500'}"
						onclick={startScreening}
						disabled={starting}
						aria-expanded={screenings.length > 1 ? choosing === 'screening' : undefined}
						data-testid="dpia-screening-button"
					>
						<i class="fa-solid fa-clipboard-check mr-1"></i>{m.dpiaScreeningStart()}
						{#if screenings.length > 1}<i class="fa-solid fa-caret-down ml-1"></i>{/if}
					</button>
				{/if}
				{#if canChange}
					<button
						type="button"
						class="btn btn-sm preset-tonal-primary"
						onclick={startEditing}
						data-testid="change-dpia-required-button"
					>
						<i class="fa-solid fa-hand-point-up mr-1"></i>{m.setDpiaRequirementManually()}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	{#if choosing && !editing}
		<ul class="flex flex-col gap-1 rounded-base border border-surface-200-800 p-1">
			{#each (choosing === 'dpia' ? dpiaForms : screenings) ?? [] as option (option.id)}
				<li>
					<button
						type="button"
						class="btn btn-sm w-full justify-start hover:preset-tonal"
						onclick={() => screen(option)}
						disabled={starting}
						data-testid="dpia-screening-option">{option.name}</button
					>
				</li>
			{/each}
		</ul>
	{/if}

	{#if editing}
		<label class="label">
			<span class="text-sm font-semibold">{m.dpiaRequired()}</span>
			<select class="select" bind:value={selected} disabled={saving}>
				<option value="true">{m.dpiaRequiredYes()}</option>
				<option value="false">{m.dpiaRequiredNo()}</option>
			</select>
		</label>
		<label class="label">
			<span class="text-sm font-semibold">{m.tierNote()}</span>
			<input class="input" bind:value={note} disabled={saving} />
			<span class="text-xs text-surface-500">{m.dpiaRequirementNoteHelpText()}</span>
		</label>
		<div class="flex gap-2 justify-end">
			<button
				type="button"
				class="btn btn-sm preset-tonal"
				disabled={saving}
				onclick={() => (editing = false)}>{m.cancel()}</button
			>
			<button
				type="button"
				class="btn btn-sm preset-filled-primary-500"
				disabled={saving}
				onclick={save}
				data-testid="save-dpia-required-button">{m.save()}</button
			>
		</div>
	{:else}
		<div class="flex flex-wrap items-center gap-3">
			{#if processing.dpia_required_source}
				<span
					class="badge {processing.dpia_required ? 'preset-tonal-error' : 'preset-tonal-success'}"
					>{processing.dpia_required ? m.dpiaRequiredYes() : m.dpiaRequiredNo()}</span
				>
				<!-- One criterion only: required by caution, not by law. -->
				{#if processing.dpia_required_source === 'assessment' && screening?.computed_outcome?.dpia_recommended}
					<span class="badge preset-tonal-warning text-xs" data-testid="dpia-recommended-badge"
						>{m.recommended()}</span
					>
				{/if}
				<span class="text-sm text-surface-600-400">
					{verdictOrigin(processing)}
					{#if screening?.id && processing.dpia_required_source !== 'manual'}
						· <a class="anchor" href={`/quick-form-responses/${screening.id}`}>{screening.ref_id}</a
						>
					{/if}
				</span>
			{:else}
				<span class="badge preset-tonal-surface">{m.notAssessed()}</span>
				<span class="text-sm text-surface-600-400">{m.dpiaNotScreenedYet()}</span>
			{/if}
		</div>
		<!-- The DPIA itself: its own row, so it never reads as part of the screening. -->
		{#if dpia || (dpia === null && processing.dpia_required && dpiaForms?.length)}
			<div class="flex flex-wrap items-center gap-3 border-t border-surface-200-800 pt-3">
				<span class="text-sm font-semibold text-surface-950-50">{m.dpia()}</span>
				{#if dpia}
					<a
						class="btn btn-sm preset-tonal-primary"
						href={`/quick-form-responses/${dpia.id}`}
						data-testid="dpia-link"
						><i class="fa-solid fa-file-shield mr-1"></i>{dpia.ref_id || dpia.name}</a
					>
					<span
						class="badge {dpia.resolution === 'accepted'
							? 'preset-tonal-success'
							: 'preset-tonal-surface'}">{safeTranslate(dpia.resolution || dpia.status)}</span
					>
				{:else if dpiaForms}
					<button
						type="button"
						class="btn btn-sm preset-filled-primary-500"
						onclick={startDpia}
						disabled={starting}
						aria-expanded={dpiaForms.length > 1 ? choosing === 'dpia' : undefined}
						data-testid="start-dpia-button"
					>
						<i class="fa-solid fa-file-shield mr-1"></i>{m.startDpia()}
						{#if dpiaForms.length > 1}<i class="fa-solid fa-caret-down ml-1"></i>{/if}
					</button>
				{/if}
			</div>
		{/if}
	{/if}

	{#if !editing}
		<p class="border-t border-surface-200-800 pt-3 text-xs text-surface-500">
			{#if loadFailed}{m.anErrorOccurred()}{:else if screenings?.length === 0}{m.noDpiaScreeningForm()}{/if}
			<a class="anchor" href="/processings/dpia">{m.dpiaStatusOverview()}</a>
		</p>
	{/if}
</div>
