<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Transition {
		value: string;
		label: string;
		side: 'any' | 'owner' | 'counterparty';
		requires_note: boolean;
		requires_date: boolean;
		allowed: boolean;
	}

	interface Cycle {
		id: string;
		state: string;
		committed_eta: string | null;
		committed_by: string | null;
		committed_at: string | null;
		notes: string | null;
		opened_at: string;
		closed_at: string | null;
	}

	// When the promise was made, as opposed to the date promised.
	const stamp = (value: string | null | undefined) =>
		value ? new Date(value).toLocaleString() : '';

	interface Payload {
		state: string;
		date_field?: string;
		date?: string | null;
		committed_eta?: string | null;
		committed_by?: string | null;
		committed_at?: string | null;
		notes?: string | null;
		reopen_count?: number;
		history?: Cycle[];
		transitions: Transition[];
	}

	interface Props {
		urlModel: string;
		object: any;
		/** Show the promise without offering to change it — used where the viewer has
		 * read-only visibility on the host field. The backend still guards the steps. */
		readOnly?: boolean;
	}

	let { urlModel, object, readOnly = false }: Props = $props();

	let payload: Payload = $state({ state: '--', transitions: [] });
	let picked: Transition | null = $state(null);
	let note = $state('');
	let promisedDate = $state('');
	let showNote = $state(false);
	let submitting = $state(false);
	let errorMessage = $state('');

	const state = $derived(payload.state ?? '--');
	const notStarted = $derived(state === '--');
	const committedEta = $derived(payload.committed_eta);
	const slipped = $derived(
		!!committedEta && !!payload.date && (payload.date as string) > (committedEta as string)
	);
	const breached = $derived(
		!!committedEta &&
			state !== 'fulfilled' &&
			(committedEta as string) < new Date().toISOString().slice(0, 10)
	);
	const noteNeeded = $derived(!!picked?.requires_note || showNote);
	const reopenCount = $derived(payload.reopen_count ?? 0);
	const history = $derived(payload.history ?? []);
	let showHistory = $state(false);

	// One verb per target state, so the button says what it does rather than
	// naming the state you land in.
	const ACTION_LABELS: Record<string, () => string> = {
		in_negotiation: m.commitmentActionNegotiate,
		committed: m.commitmentActionCommit,
		declined: m.commitmentActionDecline,
		fulfilled: m.commitmentActionFulfil
	};

	// Reopening reads differently once a promise exists: it is not "start talking", it is
	// "that promise no longer holds".
	function targetLabel(transition: Transition) {
		if (transition.value === 'in_negotiation' && state === 'committed')
			return m.commitmentActionReopen();
		return ACTION_LABELS[transition.value]?.() ?? safeTranslate(transition.value);
	}

	// Keyed on the object: a same-route navigation reuses the component, and stale
	// transitions would be confirmed against the new object's id.
	let loadToken = 0;
	async function load() {
		const token = ++loadToken;
		const res = await fetch(`/${urlModel}/${object.id}/commitment-transitions`);
		if (!res.ok || token !== loadToken) return;
		const fresh = await res.json();
		if (token !== loadToken) return;
		payload = fresh;
		picked = null;
	}

	$effect(() => {
		void urlModel;
		void object?.id;
		load();
	});

	// The backend answers with either {field: "<i18n key>"} or SvelteKit's {message}.
	async function readError(res: Response): Promise<string> {
		let body: any;
		try {
			body = await res.json();
		} catch {
			return `${m.anErrorOccurred()} (${res.status})`;
		}
		const raw = body?.message ?? body;
		const first = typeof raw === 'string' ? raw : Object.values(raw ?? {}).flat()[0];
		if (typeof first !== 'string' || !first) return `${m.anErrorOccurred()} (${res.status})`;
		const translated = safeTranslate(first);
		return translated && translated !== first ? translated : first;
	}

	function pick(transition: Transition) {
		picked = transition;
		note = '';
		showNote = false;
		errorMessage = '';
		// Prefill with the date already on the object: proposing it unchanged is the
		// common case, and it is what gets frozen on sign-off.
		promisedDate = payload.date ?? '';
	}

	async function confirm() {
		if (!picked) return;
		submitting = true;
		errorMessage = '';
		try {
			const res = await fetch(`/${urlModel}/${object.id}/commitment-transitions`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					commitment_state: picked.value,
					// Left out when empty so a step taken without a note keeps the last exchange.
					...(note.trim() ? { commitment_notes: note.trim() } : {}),
					...(picked.requires_date && promisedDate ? { commitment_date: promisedDate } : {})
				})
			});
			if (!res.ok) {
				errorMessage = await readError(res);
				return;
			}
			payload = await res.json();
			picked = null;
			await invalidateAll();
		} finally {
			submitting = false;
		}
	}
</script>

<div class="card bg-white p-4 shadow-lg space-y-3">
	<div class="flex items-center justify-between flex-wrap gap-2">
		<span class="font-semibold">{m.commitment()}</span>
		<span class="badge preset-tonal-surface">
			{notStarted ? m.commitmentNotStarted() : safeTranslate(state)}
		</span>
	</div>

	{#if committedEta}
		<div class="text-sm flex flex-wrap items-center gap-2">
			<span class="text-surface-500">{m.committedDate()}:</span>
			<span class="font-medium">{committedEta}</span>
			{#if payload.committed_by}
				<span class="text-surface-500">· {payload.committed_by}</span>
			{/if}
			{#if payload.committed_at}
				<span class="text-surface-500" title={m.commitmentTakenAt()}>
					· {stamp(payload.committed_at)}
				</span>
			{/if}
			{#if breached}
				<span class="badge preset-tonal-error">{m.commitmentBreached()}</span>
			{:else if slipped}
				<span class="badge preset-tonal-warning">{m.commitmentSlipped()}</span>
			{/if}
		</div>
	{/if}

	{#if payload.notes}
		<p class="text-sm text-surface-600-400 whitespace-pre-line">{payload.notes}</p>
	{/if}

	{#if history.length}
		<button class="text-xs anchor" type="button" onclick={() => (showHistory = !showHistory)}>
			{m.commitmentReopenedTimes({ count: reopenCount, s: reopenCount > 1 ? 's' : '' })}
		</button>
		{#if showHistory}
			<ol class="text-xs text-surface-500 space-y-1 border-l-2 border-surface-200-800 pl-3">
				{#each history as cycle}
					<li>
						<span class="font-medium">{safeTranslate(cycle.state)}</span>
						{#if cycle.committed_eta}· {cycle.committed_eta}{/if}
						{#if cycle.committed_by}· {cycle.committed_by}{/if}
						{#if cycle.committed_at}· {stamp(cycle.committed_at)}{/if}
						{#if cycle.notes}<span class="block italic">{cycle.notes}</span>{/if}
					</li>
				{/each}
			</ol>
		{/if}
	{/if}

	{#if picked}
		<div class="space-y-2 border-t border-surface-200-800 pt-3">
			<p class="text-sm font-semibold">{targetLabel(picked)}</p>

			{#if picked.requires_date}
				<label class="text-sm block" for="commitment-date">{m.commitmentDatePromised()}</label>
				<input
					id="commitment-date"
					type="date"
					class="input w-full"
					bind:value={promisedDate}
					required
				/>
			{/if}

			{#if noteNeeded}
				<textarea
					class="textarea w-full"
					rows="3"
					bind:value={note}
					placeholder={picked.requires_note
						? m.commitmentNoteRequiredHelpText()
						: m.commitmentNotes()}
				></textarea>
			{:else}
				<button class="text-xs anchor" type="button" onclick={() => (showNote = true)}>
					{m.commitmentAddANote()}
				</button>
			{/if}

			{#if errorMessage}
				<p class="text-error-500 text-xs font-medium">{errorMessage}</p>
			{/if}

			<div class="flex gap-2">
				<button
					type="button"
					class="btn preset-filled-primary-500"
					disabled={submitting ||
						(picked.requires_note && !note.trim()) ||
						(picked.requires_date && !promisedDate)}
					onclick={confirm}
				>
					{m.confirm()}
				</button>
				<button type="button" class="btn preset-tonal-surface" onclick={() => (picked = null)}>
					{m.cancel()}
				</button>
			</div>
		</div>
	{:else if readOnly}
		<!-- nothing: the state above is the whole story for a read-only viewer -->
	{:else if payload.transitions.length}
		<div class="flex flex-wrap gap-2 border-t border-surface-200-800 pt-3">
			{#each payload.transitions as transition}
				<button
					type="button"
					class="btn {transition.allowed ? 'preset-tonal-primary' : 'preset-tonal-surface'}"
					disabled={!transition.allowed}
					title={transition.allowed
						? undefined
						: transition.side === 'owner'
							? m.onlyTheAccountableActorCanDoThis()
							: m.theAccountableActorCannotCloseTheirOwnCommitment()}
					onclick={() => pick(transition)}
				>
					{targetLabel(transition)}
				</button>
			{/each}
		</div>
	{:else}
		<p class="text-xs text-surface-500 border-t border-surface-200-800 pt-3">
			{m.noCommitmentActionAvailable()}
		</p>
	{/if}
</div>
