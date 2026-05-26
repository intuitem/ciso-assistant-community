<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { pageTitle } from '$lib/utils/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import { VERDICT, VERDICT_ORDER, type Verdict } from '$lib/utils/questionnaire-verdict';
	import type { PageData } from './$types';

	interface Sheet {
		name: string;
		header_row: number;
		headers: string[];
		row_count: number;
		rows_preview: string[][];
	}

	interface Run {
		id: string;
		title: string;
		filename: string;
		status: 'pending' | 'parsing' | 'parsed' | 'failed';
		error_message: string;
		folder: { id: string; str?: string; name?: string };
		parsed_data: { sheets?: Sheet[]; active_sheet?: string };
		column_mapping: {
			sheet?: string;
			question_col?: number;
			answer_col?: number;
			comment_col?: number;
			section_col?: number;
		};
		value_mapping?: {
			yes?: string;
			partial?: string;
			no?: string;
			candidates?: string[];
			source?: 'data_validation' | 'distinct_values' | 'fallback';
			vocab_count?: number;
			has_multiple_vocabs?: boolean;
		};
		created_at: string;
	}

	interface Question {
		id: string;
		ord: number;
		ref_id: string;
		section: string;
		text: string;
		answer_candidates?: string[];
		answer_mapping?: {
			yes?: string;
			partial?: string;
			no?: string;
			candidates?: string[];
			source?: 'data_validation' | 'distinct_values' | 'fallback';
		};
	}

	interface AgentRunState {
		id: string;
		status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
		strictness: 'fast' | 'thorough';
		total_steps: number;
		completed_steps: number;
		current_step_label: string;
		last_heartbeat_at: string | null;
		started_at: string | null;
		finished_at: string | null;
		error_message: string;
		model_used: string;
		total_tokens: number;
	}

	interface AgentAction {
		id: string;
		kind: string;
		target_object_id: string;
		payload: { status?: string; comment?: string };
		rationale: string;
		source_refs: Array<{
			index: number;
			kind: string;
			id: string;
			name: string;
			score: number | null;
			snippet: string;
		}>;
		confidence: number | null;
		state: string;
		iteration: number;
	}

	let { data }: { data: PageData } = $props();

	// Map a citation `kind` (snake_case from the indexer) to a frontend route.
	// Returns null when the kind has no direct detail page (e.g. requirement_node lives in a framework,
	// document_chunk has no standalone view).
	const CITATION_KIND_TO_URLMODEL: Record<string, string> = {
		applied_control: 'applied-controls',
		risk_scenario: 'risk-scenarios',
		asset: 'assets',
		evidence: 'evidences',
		reference_control: 'reference-controls',
		requirement_assessment: 'requirement-assessments',
		vulnerability: 'vulnerabilities',
		incident: 'incidents',
		framework: 'frameworks',
		threat: 'threats',
		library_threat: 'threats',
		entity: 'entities',
		solution: 'solutions',
		feared_event: 'feared-events',
		ebios_rm_study: 'ebios-rm',
		compliance_assessment: 'compliance-assessments',
		risk_assessment: 'risk-assessments'
	};

	function getCitationHref(ref: { kind: string; id: string }): string | null {
		if (!ref?.id) return null;
		const urlModel = CITATION_KIND_TO_URLMODEL[ref.kind];
		if (!urlModel) return null;
		return `/${urlModel}/${ref.id}`;
	}

	// Polling override layers — when the client polls, we override server-side
	// load data without losing the ability to react to invalidateAll().
	let polledRun = $state<Run | null>(null);
	let polledAgentRun = $state<AgentRunState | null>(null);
	let polledActions = $state<AgentAction[] | null>(null);

	const run = $derived<Run>(polledRun ?? (data.run as Run));
	const questions = $derived<Question[]>(data.questions ?? []);
	const agentRun = $derived<AgentRunState | null>(
		polledAgentRun ?? (data.latestAgentRun as AgentRunState | null)
	);
	const actions = $derived<AgentAction[]>(
		polledActions ?? (data.actions as AgentAction[] | undefined) ?? []
	);

	$effect(() => {
		$pageTitle = run.title || run.filename;
	});

	// Same flag the index page checks. ENABLE_CHAT=false on the backend
	// removes chat_mode from featureflags entirely, so a single check covers
	// both "infrastructure off" and "admin turned it off".
	const chatEnabled = $derived(Boolean(page.data?.featureflags?.chat_mode));

	const toast = getToastStore();

	let pollHandle: ReturnType<typeof setInterval> | null = null;
	let extractBusy = $state(false);
	let startBusy = $state(false);
	let cancelBusy = $state(false);

	// Mapping form state
	let selectedSheetName = $state<string>(
		run.column_mapping?.sheet || run.parsed_data?.active_sheet || ''
	);
	let questionCol = $state<number | ''>(run.column_mapping?.question_col ?? '');
	let answerCol = $state<number | ''>(run.column_mapping?.answer_col ?? '');
	let commentCol = $state<number | ''>(run.column_mapping?.comment_col ?? '');
	let sectionCol = $state<number | ''>(run.column_mapping?.section_col ?? '');
	let saving = $state(false);

	// Strictness picker state
	let strictness = $state<'fast' | 'thorough'>('fast');

	function stopPoll() {
		if (pollHandle) {
			clearInterval(pollHandle);
			pollHandle = null;
		}
	}

	// Polling fetches swallow transient errors on purpose — a single network
	// blip would otherwise become an unhandled rejection inside setInterval
	// and silently drop further polls. We log and return; the next tick retries.
	async function refreshParseRun() {
		try {
			const res = await fetch(`/experimental/questionnaire-autopilot/${run.id}`, {
				headers: { accept: 'application/json' }
			});
			if (res.ok) {
				polledRun = await res.json();
			}
		} catch (e) {
			console.warn('refreshParseRun failed; will retry on next tick', e);
		}
	}

	async function refreshAgentRun() {
		if (!agentRun) return;
		try {
			const res = await fetch(
				`/experimental/questionnaire-autopilot/${run.id}/agent-state?run_id=${agentRun.id}`
			);
			if (!res.ok) return;
			const payload = await res.json();
			polledAgentRun = payload.agentRun;
			polledActions = payload.actions ?? [];
			if (
				polledAgentRun &&
				(polledAgentRun.status === 'succeeded' ||
					polledAgentRun.status === 'failed' ||
					polledAgentRun.status === 'cancelled')
			) {
				stopPoll();
				// Sync the freshly-completed run into the page-server load so
				// reloads don't re-fetch and so further polls see consistent state.
				await invalidateAll();
				polledRun = null;
				polledAgentRun = null;
				polledActions = null;
			}
		} catch (e) {
			console.warn('refreshAgentRun failed; will retry on next tick', e);
		}
	}

	function startPolling() {
		stopPoll();
		if (run.status === 'pending' || run.status === 'parsing') {
			pollHandle = setInterval(refreshParseRun, 1500);
			return;
		}
		if (agentRun && (agentRun.status === 'queued' || agentRun.status === 'running')) {
			pollHandle = setInterval(refreshAgentRun, 2000);
		}
	}

	onMount(startPolling);
	onDestroy(stopPoll);

	$effect(() => {
		// Restart polling when state transitions cross a boundary
		const _trigger = run.status + '|' + (agentRun?.status ?? '') + '|' + (agentRun?.id ?? '');
		void _trigger;
		startPolling();
	});

	const selectedSheet = $derived(
		run.parsed_data?.sheets?.find((s) => s.name === selectedSheetName)
	);
	const colOptions = $derived(
		selectedSheet
			? selectedSheet.headers.map((h, i) => ({ value: i, label: `${i + 1}. ${h}` }))
			: []
	);
	const canSaveMapping = $derived(
		!!selectedSheetName && questionCol !== '' && !saving && run.status === 'parsed'
	);

	function onSheetChange() {
		questionCol = '';
		answerCol = '';
		commentCol = '';
		sectionCol = '';
	}

	async function saveMapping() {
		if (!canSaveMapping) return;
		saving = true;
		try {
			const body: Record<string, string | number | null> = {
				sheet: selectedSheetName,
				question_col: questionCol as number
			};
			if (answerCol !== '') body.answer_col = answerCol;
			if (commentCol !== '') body.comment_col = commentCol;
			if (sectionCol !== '') body.section_col = sectionCol;

			const saveRes = await fetch(`/experimental/questionnaire-autopilot/${run.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			const saveResult = await saveRes.json();
			if (!saveRes.ok) {
				toast.trigger({ message: saveResult.detail || 'Failed to save mapping.' });
				return;
			}
			polledRun = { ...run, column_mapping: saveResult.column_mapping };

			// Chain the extract step so the user lands directly in the
			// configure-run phase. Failures here are surfaced but don't roll
			// back the mapping save.
			const extractRes = await fetch(`/experimental/questionnaire-autopilot/${run.id}/extract`, {
				method: 'POST'
			});
			const extractResult = await extractRes.json();
			if (!extractRes.ok) {
				toast.trigger({
					message: extractResult.detail || 'Mapping saved, but extracting the questions failed.'
				});
				return;
			}
			toast.trigger({
				message: `Mapping saved · extracted ${extractResult.extracted} questions.`
			});
			await invalidateAll();
		} finally {
			saving = false;
		}
	}

	async function extractQuestions() {
		extractBusy = true;
		try {
			const res = await fetch(`/experimental/questionnaire-autopilot/${run.id}/extract`, {
				method: 'POST'
			});
			const result = await res.json();
			if (!res.ok) {
				toast.trigger({ message: result.detail || 'Failed to extract questions.' });
				return;
			}
			toast.trigger({ message: `Extracted ${result.extracted} questions.` });
			await invalidateAll();
		} finally {
			extractBusy = false;
		}
	}

	async function startPrefill(strictnessOverride?: 'fast' | 'thorough') {
		const effectiveStrictness =
			strictnessOverride === 'fast' || strictnessOverride === 'thorough'
				? strictnessOverride
				: strictness;
		startBusy = true;
		try {
			const res = await fetch(`/experimental/questionnaire-autopilot/${run.id}/start-prefill`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ strictness: effectiveStrictness })
			});
			const result = await res.json();
			if (!res.ok) {
				toast.trigger({ message: result.detail || 'Failed to start prefill.' });
				return;
			}
			toast.trigger({ message: 'Agent run started.' });
			// Drop the polled overrides so the next poll picks up the brand-new run
			polledRun = null;
			polledAgentRun = null;
			polledActions = null;
			await invalidateAll();
		} finally {
			startBusy = false;
		}
	}

	async function runAgain(newStrictness: 'fast' | 'thorough') {
		strictness = newStrictness;
		await startPrefill(newStrictness);
	}

	// --- Per-question retry: attach existing control / suggest a new one ----

	interface ControlDraft {
		name: string;
		ref_id?: string;
		description: string;
		observation: string;
		status: string;
		category: string;
		csf_function: string;
	}

	let retryBusyForQuestion = $state<string | null>(null);

	let pickerOpenForQuestion = $state<string | null>(null);
	let pickerSelectedId = $state<string | null>(null);

	// SuperForm wrapper so we can drive the standard AutocompleteSelect
	// component (which expects a SuperForm). One-field schema, client-only.
	const pickerSchema = z.object({
		applied_control_id: z.string().nullable().optional()
	});
	const pickerForm = superForm(defaults({ applied_control_id: null }, zod(pickerSchema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(pickerSchema)
	});
	const _pickerStoreUnsub = pickerForm.form.subscribe((v: any) => {
		pickerSelectedId = v?.applied_control_id ?? null;
	});
	onDestroy(_pickerStoreUnsub);

	let suggestOpenForQuestion = $state<string | null>(null);
	let suggestLoading = $state(false);
	let suggestDraft = $state<ControlDraft | null>(null);

	// Looked up against the live questions list so the modal stays in sync
	// even if polling refreshes the list while a modal is open.
	const pickerQuestion = $derived(
		pickerOpenForQuestion ? (questions.find((q) => q.id === pickerOpenForQuestion) ?? null) : null
	);
	const suggestQuestion = $derived(
		suggestOpenForQuestion ? (questions.find((q) => q.id === suggestOpenForQuestion) ?? null) : null
	);

	function openPicker(question: Question) {
		pickerOpenForQuestion = question.id;
		pickerForm.form.set({ applied_control_id: null });
	}

	function closePicker() {
		pickerOpenForQuestion = null;
		pickerForm.form.set({ applied_control_id: null });
	}

	async function applyPickedControl() {
		if (!pickerOpenForQuestion || !pickerSelectedId) return;
		const questionId = pickerOpenForQuestion;
		const controlId = pickerSelectedId;
		retryBusyForQuestion = questionId;
		closePicker();
		try {
			const res = await fetch(
				`/experimental/questionnaire-autopilot/${run.id}/q/${questionId}/retry-with-control`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ applied_control_id: controlId })
				}
			);
			const data = await res.json();
			if (!res.ok) {
				toast.trigger({ message: data.detail || 'Retry failed.' });
				return;
			}
			toast.trigger({
				message: `Re-tried with hint · confidence ${
					typeof data.confidence === 'number' ? data.confidence.toFixed(2) : '—'
				}`
			});
			await refreshAgentRunOrInvalidate();
		} finally {
			retryBusyForQuestion = null;
		}
	}

	async function openSuggest(question: Question) {
		suggestOpenForQuestion = question.id;
		suggestLoading = true;
		suggestDraft = null;
		try {
			const res = await fetch(
				`/experimental/questionnaire-autopilot/${run.id}/q/${question.id}/suggest-control`,
				{ method: 'POST' }
			);
			const data = await res.json();
			if (!res.ok) {
				toast.trigger({ message: data.detail || 'Failed to draft a control.' });
				suggestOpenForQuestion = null;
				return;
			}
			suggestDraft = {
				name: data.name || '',
				ref_id: '',
				description: data.description || '',
				observation: data.observation || '',
				status: data.status || 'to_do',
				category: data.category || '',
				csf_function: data.csf_function || ''
			};
		} finally {
			suggestLoading = false;
		}
	}

	function closeSuggest() {
		suggestOpenForQuestion = null;
		suggestDraft = null;
	}

	async function commitSuggested() {
		if (!suggestOpenForQuestion || !suggestDraft) return;
		if (!suggestDraft.name.trim()) {
			toast.trigger({ message: 'Name is required.' });
			return;
		}
		const questionId = suggestOpenForQuestion;
		const draft = suggestDraft;
		retryBusyForQuestion = questionId;
		closeSuggest();
		try {
			const res = await fetch(
				`/experimental/questionnaire-autopilot/${run.id}/q/${questionId}/create-and-retry`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(draft)
				}
			);
			const data = await res.json();
			if (!res.ok && res.status !== 207) {
				toast.trigger({ message: data.detail || 'Failed to create the control.' });
				return;
			}
			if (res.status === 207) {
				toast.trigger({
					message: `Control created — but retry failed: ${data.detail ?? ''}`
				});
			} else {
				toast.trigger({
					message: `Control created & retry done · confidence ${
						typeof data.confidence === 'number' ? data.confidence.toFixed(2) : '—'
					}`
				});
			}
			await refreshAgentRunOrInvalidate();
		} finally {
			retryBusyForQuestion = null;
		}
	}

	async function refreshAgentRunOrInvalidate() {
		// Easiest: pull fresh agent state if we have a run; otherwise invalidate the
		// page-server load. Either way the row redraws.
		if (agentRun) {
			await refreshAgentRun();
		}
		await invalidateAll();
	}

	async function cancelRun() {
		if (!agentRun) return;
		cancelBusy = true;
		try {
			const res = await fetch(
				`/experimental/questionnaire-autopilot/${run.id}/cancel-agent?run_id=${agentRun.id}`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' }
				}
			);
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				toast.trigger({ message: err.detail || 'Failed to cancel.' });
				return;
			}
			toast.trigger({ message: 'Cancellation requested.' });
			await refreshAgentRun();
		} finally {
			cancelBusy = false;
		}
	}

	const phase = $derived.by(() => {
		if (run.status === 'pending' || run.status === 'parsing') return 'parsing';
		if (run.status === 'failed') return 'parse_failed';
		if (!run.column_mapping?.sheet) return 'mapping';
		if (questions.length === 0) return 'extract';
		if (!agentRun) return 'configure_run';
		if (agentRun.status === 'queued' || agentRun.status === 'running') return 'running';
		if (agentRun.status === 'succeeded') return 'review';
		if (agentRun.status === 'failed' || agentRun.status === 'cancelled') return 'run_ended';
		return 'configure_run';
	});

	let nowTick = $state(Date.now());
	onMount(() => {
		const handle = setInterval(() => (nowTick = Date.now()), 1000);
		return () => clearInterval(handle);
	});

	const heartbeatStaleness = $derived.by(() => {
		if (!agentRun?.last_heartbeat_at) return null;
		const hb = new Date(agentRun.last_heartbeat_at).getTime();
		return Math.floor((nowTick - hb) / 1000);
	});

	function formatDuration(ms: number): string {
		if (ms < 0 || !Number.isFinite(ms)) return '—';
		const totalSec = Math.floor(ms / 1000);
		const h = Math.floor(totalSec / 3600);
		const m = Math.floor((totalSec % 3600) / 60);
		const s = totalSec % 60;
		if (h > 0) return `${h}h ${m}m ${s}s`;
		if (m > 0) return `${m}m ${s}s`;
		return `${s}s`;
	}

	function formatTimestamp(iso: string | null): string {
		return iso ? new Date(iso).toLocaleString() : '—';
	}

	const runDurationMs = $derived.by(() => {
		if (!agentRun?.started_at) return null;
		const start = new Date(agentRun.started_at).getTime();
		const end = agentRun.finished_at ? new Date(agentRun.finished_at).getTime() : nowTick;
		return end - start;
	});

	// Action by question id (latest, non-expired)
	const actionByQuestion = $derived.by(() => {
		const m: Record<string, AgentAction> = {};
		for (const a of actions) {
			if (a.kind !== 'propose_answer') continue;
			if (a.state === 'expired') continue;
			const existing = m[a.target_object_id];
			if (!existing || a.iteration > existing.iteration) {
				m[a.target_object_id] = a;
			}
		}
		return m;
	});
	const answeredCount = $derived(Object.keys(actionByQuestion).length);

	const statusBreakdown = $derived.by(() => {
		const counts: Record<Verdict, number> = {
			[VERDICT.YES]: 0,
			[VERDICT.PARTIAL]: 0,
			[VERDICT.NO]: 0,
			[VERDICT.NEEDS_INFO]: 0
		};
		for (const q of questions) {
			const a = actionByQuestion[q.id];
			if (!a) continue;
			const s = (a.payload.status as Verdict) || VERDICT.NEEDS_INFO;
			if (s in counts) counts[s] += 1;
			else counts[VERDICT.NEEDS_INFO] += 1;
		}
		const labels: Record<Verdict, string> = {
			[VERDICT.YES]: 'Yes',
			[VERDICT.PARTIAL]: 'Partial',
			[VERDICT.NO]: 'No',
			[VERDICT.NEEDS_INFO]: 'Needs info'
		};
		const colors: Record<Verdict, string> = {
			[VERDICT.YES]: 'bg-green-500',
			[VERDICT.PARTIAL]: 'bg-yellow-500',
			[VERDICT.NO]: 'bg-red-500',
			[VERDICT.NEEDS_INFO]: 'bg-gray-400'
		};
		const pillColors: Record<Verdict, string> = {
			[VERDICT.YES]: 'bg-green-100 text-green-800',
			[VERDICT.PARTIAL]: 'bg-yellow-100 text-yellow-800',
			[VERDICT.NO]: 'bg-red-100 text-red-800',
			[VERDICT.NEEDS_INFO]: 'bg-gray-100 text-gray-700'
		};
		return VERDICT_ORDER.map((s) => ({
			status: s,
			label: labels[s],
			color: colors[s],
			pillColor: pillColors[s],
			count: counts[s],
			pct: answeredCount > 0 ? Math.round((counts[s] / answeredCount) * 100) : 0
		}));
	});

	const pendingCount = $derived(questions.length - answeredCount);

	// Confidence threshold above which we treat the answer as "good to go" by
	// default. The reviewer can still expand the auto-accepted band to spot-check.
	const AUTO_ACCEPT_THRESHOLD = 0.85;

	const sortedQuestions = $derived.by(() => {
		// Order by confidence ascending (worst first), then by ord
		return [...questions].sort((a, b) => {
			const ca = actionByQuestion[a.id]?.confidence ?? -1;
			const cb = actionByQuestion[b.id]?.confidence ?? -1;
			if (ca !== cb) return ca - cb;
			return a.ord - b.ord;
		});
	});

	// `needs_info` always lands in the review band even with high confidence:
	// the agent might be very sure we *don't* have evidence, but the human
	// still has to act on it (attach a control, suggest one, leave blank).
	const needsReviewQuestions = $derived(
		sortedQuestions.filter((q) => {
			const a = actionByQuestion[q.id];
			if (!a) return true;
			if (a.payload?.status === VERDICT.NEEDS_INFO) return true;
			const c = a.confidence;
			return c == null || c < AUTO_ACCEPT_THRESHOLD;
		})
	);
	const autoAcceptedQuestions = $derived(
		sortedQuestions.filter((q) => {
			const a = actionByQuestion[q.id];
			if (!a) return false;
			if (a.payload?.status === VERDICT.NEEDS_INFO) return false;
			const c = a.confidence;
			return c != null && c >= AUTO_ACCEPT_THRESHOLD;
		})
	);
	let autoAcceptedExpanded = $state(false);

	function statusPill(status: string) {
		const map: Record<string, string> = {
			[VERDICT.YES]: 'bg-green-100 text-green-800',
			[VERDICT.NO]: 'bg-red-100 text-red-800',
			[VERDICT.PARTIAL]: 'bg-yellow-100 text-yellow-800',
			[VERDICT.NEEDS_INFO]: 'bg-gray-100 text-gray-700'
		};
		return map[status] || 'bg-gray-100 text-gray-700';
	}

	// Confidence uses a mono-indigo intensity scale so it visually reads as a
	// meter ("how sure the agent is"), distinct from the status pills' green /
	// yellow / red / gray which encode the verdict ("what the answer is").
	function confidenceBar(c: number | null) {
		if (c == null) return { width: '0%', color: 'bg-gray-200' };
		const pct = Math.max(0, Math.min(1, c)) * 100;
		const color = c >= 0.8 ? 'bg-indigo-600' : c >= 0.5 ? 'bg-indigo-400' : 'bg-indigo-200';
		return { width: `${pct.toFixed(0)}%`, color };
	}
</script>

{#if !chatEnabled}
	<div class="bg-white shadow-sm py-6 px-6 card max-w-2xl border-l-4 border-amber-400">
		<h4 class="h4 font-bold">
			<i class="fa-solid fa-robot mr-2 text-amber-600"></i>AI chat is required
		</h4>
		<p class="text-sm text-gray-700 mt-2">
			This run is still available, but Questionnaire Autopilot needs the same LLM and retrieval
			pipeline as AI Chat — currently disabled on this deployment.
		</p>
		<p class="text-xs text-gray-500 mt-2">
			Ask an administrator to enable <code class="font-mono">ENABLE_CHAT</code> on the backend and
			turn on the <em>chat mode</em> feature flag in Settings.
		</p>
	</div>
{:else}
	<div class="space-y-4">
		<!-- Header -->
		<div class="bg-white shadow-sm py-3 px-6 card flex items-center justify-between">
			<div>
				<a
					href="/experimental/questionnaire-autopilot"
					class="text-xs text-gray-500 hover:text-gray-700"
				>
					<i class="fa-solid fa-chevron-left mr-1"></i>All runs
				</a>
				<h4 class="h4 font-bold mt-1 font-mono">{run.title || run.filename}</h4>
				{#if run.title && run.filename && run.title !== run.filename}
					<div class="text-xs text-gray-500 mt-0.5">
						<i class="fa-solid fa-file-excel mr-1"></i>{run.filename}
					</div>
				{/if}
				<div class="text-xs text-gray-500 mt-1">
					Domain: {run.folder?.str || run.folder?.name || '—'} · Uploaded
					{new Date(run.created_at).toLocaleString()}
				</div>
			</div>
			<div class="text-right space-y-1">
				<span
					class="text-xs px-2 py-0.5 rounded font-medium uppercase tracking-wide
				{run.status === 'parsed'
						? 'bg-green-100 text-green-800'
						: run.status === 'failed'
							? 'bg-red-100 text-red-800'
							: 'bg-yellow-100 text-yellow-800'}"
				>
					file: {run.status}
				</span>
				{#if agentRun}
					<div>
						<span
							class="text-xs px-2 py-0.5 rounded font-medium uppercase tracking-wide
						{agentRun.status === 'succeeded'
								? 'bg-green-100 text-green-800'
								: agentRun.status === 'failed' || agentRun.status === 'cancelled'
									? 'bg-red-100 text-red-800'
									: 'bg-blue-100 text-blue-800'}"
						>
							agent: {agentRun.status}
						</span>
					</div>
				{/if}
			</div>
		</div>

		{#if phase === 'parsing'}
			<div class="bg-white shadow-sm py-6 px-6 card text-center">
				<i class="fa-solid fa-spinner fa-spin text-2xl text-blue-500"></i>
				<p class="mt-2 text-sm text-gray-600">Parsing the workbook…</p>
			</div>
		{:else if phase === 'parse_failed'}
			<div class="bg-white shadow-sm py-4 px-6 card border-l-4 border-red-500">
				<div class="font-semibold text-red-700">Parsing failed</div>
				<div class="text-sm text-gray-700 mt-1 font-mono whitespace-pre-wrap">
					{run.error_message || 'Unknown error.'}
				</div>
			</div>
		{:else if phase === 'mapping' && run.parsed_data?.sheets}
			<div class="grid grid-cols-3 gap-4">
				<div class="col-span-1 bg-white shadow-sm py-4 px-6 card space-y-4">
					<div>
						<h5 class="font-semibold text-sm mb-2">1. Pick the sheet</h5>
						<select
							class="w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
							bind:value={selectedSheetName}
							onchange={onSheetChange}
						>
							{#each run.parsed_data.sheets as sheet}
								<option value={sheet.name}>
									{sheet.name} ({sheet.row_count} row{sheet.row_count === 1 ? '' : 's'})
								</option>
							{/each}
						</select>
					</div>

					{#if selectedSheet}
						<div class="space-y-3">
							<h5 class="font-semibold text-sm">2. Map the columns</h5>

							<div>
								<label for="qcol" class="block text-xs font-medium text-gray-700">
									Question column *
								</label>
								<select
									id="qcol"
									class="mt-1 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
									bind:value={questionCol}
								>
									<option value="">— select —</option>
									{#each colOptions as opt}
										<option value={opt.value}>{opt.label}</option>
									{/each}
								</select>
							</div>

							<div>
								<label for="acol" class="block text-xs font-medium text-gray-700">
									Answer / Status column
								</label>
								<select
									id="acol"
									class="mt-1 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
									bind:value={answerCol}
								>
									<option value="">— optional —</option>
									{#each colOptions as opt}
										<option value={opt.value}>{opt.label}</option>
									{/each}
								</select>
							</div>

							<div>
								<label for="ccol" class="block text-xs font-medium text-gray-700">
									Comment column
								</label>
								<select
									id="ccol"
									class="mt-1 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
									bind:value={commentCol}
								>
									<option value="">— optional —</option>
									{#each colOptions as opt}
										<option value={opt.value}>{opt.label}</option>
									{/each}
								</select>
							</div>

							<div>
								<label for="scol" class="block text-xs font-medium text-gray-700">
									Section column
								</label>
								<select
									id="scol"
									class="mt-1 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
									bind:value={sectionCol}
								>
									<option value="">— optional —</option>
									{#each colOptions as opt}
										<option value={opt.value}>{opt.label}</option>
									{/each}
								</select>
							</div>

							<button
								type="button"
								class="btn preset-filled w-full"
								disabled={!canSaveMapping}
								onclick={saveMapping}
							>
								{saving ? 'Saving & extracting…' : 'Save mapping & extract questions'}
							</button>
						</div>
					{/if}
				</div>

				<div class="col-span-2 bg-white shadow-sm py-4 px-6 card overflow-x-auto">
					<h5 class="font-semibold text-sm mb-2">
						Preview — first {selectedSheet?.rows_preview.length ?? 0} of
						{selectedSheet?.row_count ?? 0} rows
					</h5>
					{#if selectedSheet && selectedSheet.headers.length > 0}
						<table class="text-xs w-full border-collapse">
							<thead>
								<tr class="bg-gray-50">
									{#each selectedSheet.headers as header, i}
										<th
											class="border border-gray-200 px-2 py-1 text-left font-semibold
										{i === questionCol ? 'bg-pink-100' : ''}
										{i === answerCol ? 'bg-blue-100' : ''}
										{i === commentCol ? 'bg-yellow-100' : ''}
										{i === sectionCol ? 'bg-purple-100' : ''}"
										>
											<span class="text-gray-400 mr-1">{i + 1}.</span>
											{header}
										</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each selectedSheet.rows_preview as row}
									<tr>
										{#each row as cell, i}
											<td
												class="border border-gray-200 px-2 py-1 align-top
											{i === questionCol ? 'bg-pink-50' : ''}
											{i === answerCol ? 'bg-blue-50' : ''}
											{i === commentCol ? 'bg-yellow-50' : ''}
											{i === sectionCol ? 'bg-purple-50' : ''}"
											>
												<div class="line-clamp-3">{cell}</div>
											</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<p class="text-sm text-gray-500">This sheet appears empty.</p>
					{/if}
				</div>
			</div>
		{:else if phase === 'extract'}
			<div class="bg-white shadow-sm py-6 px-6 card flex items-center justify-between">
				<div>
					<div class="font-semibold">Mapping saved.</div>
					<div class="text-sm text-gray-600 mt-1">
						Sheet: <span class="font-mono">{run.column_mapping.sheet}</span> · Question column:
						<span class="font-mono">{(run.column_mapping.question_col ?? 0) + 1}</span>
						{#if run.column_mapping.section_col != null}
							· Section column: <span class="font-mono"
								>{(run.column_mapping.section_col ?? 0) + 1}</span
							>
						{/if}
					</div>
					<p class="text-sm text-gray-500 mt-2">
						Next step: extract the questions into individual records so the agent can answer each
						one.
					</p>
				</div>
				<button
					type="button"
					class="btn preset-filled"
					disabled={extractBusy}
					onclick={extractQuestions}
				>
					{extractBusy ? 'Extracting…' : 'Extract questions'}
				</button>
			</div>
		{:else if phase === 'configure_run'}
			<div class="bg-white shadow-sm py-6 px-6 card space-y-4">
				<div>
					<div class="font-semibold">{questions.length} questions extracted.</div>
					<p class="text-sm text-gray-600 mt-1">
						Pick how the agent should work, then start the prefill. You'll see live progress — no
						need to keep this page focused.
					</p>
					<p class="text-xs text-gray-500 mt-2 flex items-start gap-1.5">
						<i class="fa-solid fa-arrows-rotate mt-0.5 text-blue-500"></i>
						<span>
							When you start, we first refresh the domain's vector index (drops stale entries, picks
							up new controls). Adds ~10–30 s before answering begins.
						</span>
					</p>
				</div>
				<div class="space-y-2">
					<label
						class="flex items-start gap-3 p-3 rounded border-2 cursor-pointer
					{strictness === 'fast' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}"
					>
						<input
							type="radio"
							name="strictness"
							value="fast"
							bind:group={strictness}
							class="mt-1"
						/>
						<div>
							<div class="font-medium">Fast</div>
							<div class="text-xs text-gray-600">
								Single pass per question, no critic. Lower confidence on the proposals; best when
								you want a quick draft to edit.
							</div>
						</div>
					</label>
					<label
						class="flex items-start gap-3 p-3 rounded border-2 cursor-pointer
					{strictness === 'thorough' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}"
					>
						<input
							type="radio"
							name="strictness"
							value="thorough"
							bind:group={strictness}
							class="mt-1"
						/>
						<div>
							<div class="font-medium">Thorough</div>
							<div class="text-xs text-gray-600">
								Critic step + one retry on low-confidence answers. ~3–5× the cost and time of Fast;
								better grounding on the answers we keep.
							</div>
						</div>
					</label>
				</div>
				<div class="flex gap-2">
					<button
						type="button"
						class="btn preset-filled"
						disabled={startBusy}
						onclick={() => startPrefill()}
					>
						<i class="fa-solid fa-play mr-2"></i>
						{startBusy ? 'Starting…' : 'Start prefill'}
					</button>
				</div>
			</div>
		{:else if phase === 'running' && agentRun}
			<div class="bg-white shadow-sm py-6 px-6 card space-y-4">
				<div class="flex items-center justify-between">
					<div>
						<h5 class="font-semibold">
							<i class="fa-solid fa-robot mr-2 text-blue-500"></i>Agent is working
						</h5>
						<div class="text-xs text-gray-500 mt-1">
							Strictness: {agentRun.strictness} · Model: {agentRun.model_used || '—'} · Tokens: {agentRun.total_tokens.toLocaleString()}
						</div>
						<div class="text-xs text-gray-500 mt-0.5">
							Started: {formatTimestamp(agentRun.started_at)} · Elapsed:
							{runDurationMs != null ? formatDuration(runDurationMs) : '—'}
						</div>
					</div>
					<button
						type="button"
						class="btn preset-tonal-error"
						disabled={cancelBusy}
						onclick={cancelRun}
					>
						{cancelBusy ? 'Cancelling…' : 'Cancel'}
					</button>
				</div>

				<div>
					<div class="flex justify-between text-xs text-gray-600 mb-1">
						<span>{agentRun.completed_steps} / {agentRun.total_steps} questions</span>
						<span>
							{agentRun.total_steps > 0
								? Math.floor((agentRun.completed_steps / agentRun.total_steps) * 100)
								: 0}%
						</span>
					</div>
					<div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
						<div
							class="bg-blue-500 h-2 transition-all duration-500"
							style="width: {agentRun.total_steps > 0
								? (agentRun.completed_steps / agentRun.total_steps) * 100
								: 0}%"
						></div>
					</div>
				</div>

				{#if agentRun.current_step_label}
					<div class="text-sm font-mono bg-gray-50 px-3 py-2 rounded">
						{agentRun.current_step_label}
					</div>
				{/if}

				<div class="text-xs">
					{#if heartbeatStaleness != null && heartbeatStaleness > 60}
						<span class="text-red-600 font-semibold">
							<i class="fa-solid fa-triangle-exclamation mr-1"></i>
							No heartbeat for {heartbeatStaleness}s — agent may be stuck. Consider cancelling.
						</span>
					{:else if heartbeatStaleness != null}
						<span class="text-gray-500">
							<i class="fa-solid fa-heart-pulse mr-1 text-green-500"></i>
							Last heartbeat {heartbeatStaleness}s ago
						</span>
					{/if}
				</div>
			</div>

			{#if answeredCount > 0}
				{@render statsBreakdown()}
				{@render bandedReview('Answers drafted so far — populating live')}
			{/if}
		{:else if phase === 'review' && agentRun}
			<div class="bg-white shadow-sm py-4 px-6 card space-y-3">
				<div class="flex items-start justify-between gap-4">
					<div>
						<h5 class="font-semibold">
							<i class="fa-solid fa-circle-check mr-2 text-green-500"></i>Run complete —
							{answeredCount} of {questions.length} answered
						</h5>
						<div class="text-xs text-gray-500 mt-1">
							{agentRun.strictness} mode · {agentRun.model_used || '—'} ·
							{agentRun.total_tokens.toLocaleString()} tokens
						</div>
						<div class="text-xs text-gray-500 mt-0.5">
							Started: {formatTimestamp(agentRun.started_at)} · Finished:
							{formatTimestamp(agentRun.finished_at)} · Duration:
							{runDurationMs != null ? formatDuration(runDurationMs) : '—'}
						</div>
					</div>
					<div class="flex flex-col items-end gap-2 text-xs">
						<a
							href="/experimental/questionnaire-autopilot/{run.id}/export"
							download
							class="btn btn-sm preset-filled"
						>
							<i class="fa-solid fa-file-arrow-down mr-1"></i>Download filled xlsx
						</a>
						{@render valueMappingHint()}
						<div class="flex flex-col items-end gap-1">
							<div class="text-gray-500">Run again with:</div>
							<div class="flex gap-2">
								<button
									type="button"
									class="btn btn-sm preset-tonal"
									disabled={startBusy}
									onclick={() => runAgain('fast')}
								>
									<i class="fa-solid fa-bolt mr-1"></i>Fast
								</button>
								<button
									type="button"
									class="btn btn-sm preset-tonal"
									disabled={startBusy}
									onclick={() => runAgain('thorough')}
								>
									<i class="fa-solid fa-magnifying-glass-chart mr-1"></i>Thorough
								</button>
							</div>
							<div class="text-[10px] text-gray-400 mt-0.5 max-w-[260px] text-right">
								<i class="fa-solid fa-arrows-rotate mr-1 text-blue-500"></i>
								Re-runs the domain index refresh first, then the prefill.
							</div>
						</div>
					</div>
				</div>
			</div>

			{@render statsBreakdown()}
			{@render bandedReview('Sorted by confidence ascending — the gnarly ones come first.')}
		{:else if phase === 'run_ended' && agentRun}
			<div class="bg-white shadow-sm py-4 px-6 card border-l-4 border-red-500 space-y-3">
				<div class="flex items-start justify-between gap-4">
					<div>
						<div class="font-semibold text-red-700">
							Run {agentRun.status === 'cancelled' ? 'cancelled' : 'failed'}
						</div>
						<div class="text-xs text-gray-500 mt-1">
							{agentRun.strictness} mode · {agentRun.model_used || '—'} ·
							{agentRun.total_tokens.toLocaleString()} tokens
						</div>
						<div class="text-xs text-gray-500 mt-0.5">
							Started: {formatTimestamp(agentRun.started_at)} · Ended:
							{formatTimestamp(agentRun.finished_at)} · Duration:
							{runDurationMs != null ? formatDuration(runDurationMs) : '—'}
						</div>
						<div class="text-xs text-gray-500 mt-1">
							Completed {agentRun.completed_steps} of {agentRun.total_steps} questions before stopping.
						</div>
					</div>
					<div class="flex flex-col items-end gap-2 text-xs">
						{#if answeredCount > 0}
							<a
								href="/experimental/questionnaire-autopilot/{run.id}/export"
								download
								class="btn btn-sm preset-filled"
							>
								<i class="fa-solid fa-file-arrow-down mr-1"></i>Download partial xlsx
							</a>
							{@render valueMappingHint()}
						{/if}
						<div class="flex flex-col items-end gap-1">
							<div class="text-gray-500">Run again with:</div>
							<div class="flex gap-2">
								<button
									type="button"
									class="btn btn-sm preset-tonal"
									disabled={startBusy}
									onclick={() => runAgain('fast')}
								>
									<i class="fa-solid fa-bolt mr-1"></i>Fast
								</button>
								<button
									type="button"
									class="btn btn-sm preset-tonal"
									disabled={startBusy}
									onclick={() => runAgain('thorough')}
								>
									<i class="fa-solid fa-magnifying-glass-chart mr-1"></i>Thorough
								</button>
							</div>
							<div class="text-[10px] text-gray-400 mt-0.5 max-w-[260px] text-right">
								<i class="fa-solid fa-arrows-rotate mr-1 text-blue-500"></i>
								Re-runs the domain index refresh first, then the prefill.
							</div>
						</div>
					</div>
				</div>
				{#if agentRun.error_message}
					<div
						class="text-sm text-gray-700 font-mono whitespace-pre-wrap bg-gray-50 px-3 py-2 rounded"
					>
						{agentRun.error_message}
					</div>
				{/if}
			</div>

			{#if answeredCount > 0}
				{@render statsBreakdown()}
				{@render bandedReview(
					`${answeredCount} partial answer${answeredCount === 1 ? '' : 's'} drafted before the run stopped.`
				)}
			{/if}
		{/if}
	</div>

	<!-- ============== Pick existing control modal ============== -->
	{#if pickerOpenForQuestion}
		<div
			class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
			role="dialog"
			aria-modal="true"
			onclick={(e) => {
				if (e.target === e.currentTarget) closePicker();
			}}
		>
			<div class="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col">
				<div class="px-6 py-4 border-b">
					<h4 class="font-semibold">Use an existing applied control</h4>
					<p class="text-xs text-gray-500 mt-1">
						Pick a control in this domain. The agent will re-run the question with it as priority
						context.
					</p>
				</div>
				{#if pickerQuestion}
					<div class="px-6 py-3 bg-gray-50 border-b">
						<div class="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">
							Question
						</div>
						<div class="text-sm mt-1">{pickerQuestion.text}</div>
						{#if pickerQuestion.section || pickerQuestion.ref_id}
							<div class="text-xs text-gray-500 mt-1 flex items-center gap-2">
								{#if pickerQuestion.section}
									<span>{pickerQuestion.section}</span>
								{/if}
								{#if pickerQuestion.ref_id}
									<span class="font-mono">· {pickerQuestion.ref_id}</span>
								{/if}
							</div>
						{/if}
					</div>
				{/if}
				<div class="px-6 py-4">
					<AutocompleteSelect
						form={pickerForm}
						field="applied_control_id"
						optionsEndpoint="applied-controls"
						optionsDetailedUrlParameters={[['folder', run.folder.id]]}
						optionsExtraFields={[['folder', 'str']]}
						label="Applied control"
					/>
				</div>
				<div class="px-6 py-3 border-t flex justify-end gap-2">
					<button type="button" class="btn" onclick={closePicker}>Cancel</button>
					<button
						type="button"
						class="btn preset-filled"
						onclick={applyPickedControl}
						disabled={!pickerSelectedId}
					>
						<i class="fa-solid fa-rotate mr-1"></i>Re-try with this control
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- ============== Suggest a new control modal ============== -->
	{#if suggestOpenForQuestion}
		<div
			class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
			role="dialog"
			aria-modal="true"
			onclick={(e) => {
				if (e.target === e.currentTarget) closeSuggest();
			}}
		>
			<div class="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
				<div class="px-6 py-4 border-b">
					<h4 class="font-semibold">Suggest a control to create</h4>
					<p class="text-xs text-gray-500 mt-1">
						Review the draft, edit anything, then create. We'll add the control to the domain and
						immediately re-try the question with it.
					</p>
				</div>
				{#if suggestQuestion}
					<div class="px-6 py-3 bg-gray-50 border-b">
						<div class="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">
							Question
						</div>
						<div class="text-sm mt-1">{suggestQuestion.text}</div>
						{#if suggestQuestion.section || suggestQuestion.ref_id}
							<div class="text-xs text-gray-500 mt-1 flex items-center gap-2">
								{#if suggestQuestion.section}
									<span>{suggestQuestion.section}</span>
								{/if}
								{#if suggestQuestion.ref_id}
									<span class="font-mono">· {suggestQuestion.ref_id}</span>
								{/if}
							</div>
						{/if}
					</div>
				{/if}

				{#if suggestLoading || !suggestDraft}
					<div class="px-6 py-12 text-center text-sm text-gray-500">
						<i class="fa-solid fa-wand-magic-sparkles fa-pulse mr-2 text-blue-500"></i>
						Drafting a control from the question…
					</div>
				{:else}
					<div class="flex-1 overflow-y-auto px-6 py-4 space-y-3 text-sm">
						{#if !suggestDraft.name && !suggestDraft.description && !suggestDraft.observation}
							<div
								class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2"
							>
								<i class="fa-solid fa-triangle-exclamation mr-1"></i>
								The LLM didn't return a draft (model may be unavailable). You can still fill the fields
								in manually and create the control.
							</div>
						{/if}
						<div>
							<label for="d-name" class="block text-xs font-medium text-gray-700"> Name * </label>
							<input
								id="d-name"
								type="text"
								bind:value={suggestDraft.name}
								maxlength="200"
								class="mt-1 w-full rounded-lg border-gray-300 sm:text-sm"
							/>
						</div>
						<div>
							<label for="d-desc" class="block text-xs font-medium text-gray-700">
								Description
							</label>
							<textarea
								id="d-desc"
								bind:value={suggestDraft.description}
								rows="3"
								class="mt-1 w-full rounded-lg border-gray-300 sm:text-sm"
							></textarea>
						</div>
						<div>
							<label for="d-status" class="block text-xs font-medium text-gray-700"> Status </label>
							<select
								id="d-status"
								bind:value={suggestDraft.status}
								class="mt-1 w-full rounded-lg border-gray-300 sm:text-sm"
							>
								<option value="to_do">To do</option>
								<option value="in_progress">In progress</option>
								<option value="active">Active</option>
								<option value="on_hold">On hold</option>
								<option value="degraded">Degraded</option>
							</select>
						</div>
						<p class="text-[11px] text-gray-400">
							The agent's drafted observation, category and CSF function will be saved along with
							the control — you can refine them later from the Applied Controls page.
						</p>
					</div>
				{/if}

				<div class="px-6 py-3 border-t flex justify-end gap-2">
					<button type="button" class="btn" onclick={closeSuggest}>Cancel</button>
					<button
						type="button"
						class="btn preset-filled"
						onclick={commitSuggested}
						disabled={!suggestDraft || !suggestDraft.name?.trim() || suggestLoading}
					>
						<i class="fa-solid fa-plus mr-1"></i>Create &amp; retry
					</button>
				</div>
			</div>
		</div>
	{/if}
{/if}

{#snippet bandedReview(needsReviewHeader: string)}
	{#if needsReviewQuestions.length > 0}
		{@render reviewList(needsReviewHeader, needsReviewQuestions)}
	{/if}

	{#if autoAcceptedQuestions.length > 0}
		<div class="bg-white shadow-sm card overflow-hidden">
			<button
				type="button"
				class="w-full flex items-center justify-between px-6 py-3 bg-green-50
					hover:bg-green-100 text-left transition-colors"
				onclick={() => (autoAcceptedExpanded = !autoAcceptedExpanded)}
			>
				<div class="flex items-center gap-2">
					<i class="fa-solid fa-circle-check text-green-600"></i>
					<span class="text-sm font-medium text-green-900">
						Auto-accepted — {autoAcceptedQuestions.length}
						{autoAcceptedQuestions.length === 1 ? 'answer' : 'answers'}
					</span>
					<span class="text-xs text-green-700">
						confidence ≥ {AUTO_ACCEPT_THRESHOLD.toFixed(2)}
					</span>
				</div>
				<i
					class="fa-solid {autoAcceptedExpanded
						? 'fa-chevron-up'
						: 'fa-chevron-down'} text-green-700 text-xs"
				></i>
			</button>
			{#if autoAcceptedExpanded}
				<div class="divide-y divide-gray-200">
					{#each autoAcceptedQuestions as question}
						{@const action = actionByQuestion[question.id]}
						{@const bar = confidenceBar(action?.confidence ?? null)}
						<div class="px-6 py-4 space-y-2">
							<div class="flex items-start justify-between gap-4">
								<div class="flex-1">
									<div class="flex items-center gap-2 text-xs text-gray-500">
										{#if question.section}
											<span class="font-medium">{question.section}</span>
										{/if}
										{#if question.ref_id}
											<span class="font-mono">{question.ref_id}</span>
										{/if}
									</div>
									<div class="text-sm mt-1">{question.text}</div>
								</div>
								{#if action}
									<div class="flex flex-col items-end gap-1 min-w-[140px]">
										<span
											class="text-xs px-2 py-0.5 rounded font-medium uppercase tracking-wide
											{statusPill(action.payload.status || VERDICT.NEEDS_INFO)}"
										>
											{action.payload.status ?? VERDICT.NEEDS_INFO}
										</span>
										<div class="w-32">
											<div class="flex justify-between text-[10px] text-gray-500">
												<span>conf.</span>
												<span>
													{action.confidence != null ? action.confidence.toFixed(2) : '—'}
												</span>
											</div>
											<div class="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
												<div class="{bar.color} h-1.5" style="width: {bar.width}"></div>
											</div>
										</div>
									</div>
								{/if}
							</div>
							{#if action}
								<div class="text-sm bg-gray-50 px-3 py-2 rounded whitespace-pre-wrap">
									{action.payload.comment || '(no comment)'}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
{/snippet}

{#snippet reviewList(headerText: string, qList: Question[])}
	<div class="bg-white shadow-sm card overflow-hidden">
		<div class="px-6 py-3 bg-gray-50 text-xs text-gray-600 border-b">
			{headerText}
		</div>
		<div class="divide-y divide-gray-200">
			{#each qList as question}
				{@const action = actionByQuestion[question.id]}
				{@const bar = confidenceBar(action?.confidence ?? null)}
				<div class="px-6 py-4 space-y-2">
					<div class="flex items-start justify-between gap-4">
						<div class="flex-1">
							<div class="flex items-center gap-2 text-xs text-gray-500">
								{#if question.section}
									<span class="font-medium">{question.section}</span>
								{/if}
								{#if question.ref_id}
									<span class="font-mono">{question.ref_id}</span>
								{/if}
							</div>
							<div class="text-sm mt-1">{question.text}</div>
						</div>
						{#if action}
							<div class="flex flex-col items-end gap-1 min-w-[140px]">
								<span
									class="text-xs px-2 py-0.5 rounded font-medium uppercase tracking-wide
									{statusPill(action.payload.status || VERDICT.NEEDS_INFO)}"
								>
									{action.payload.status ?? VERDICT.NEEDS_INFO}
								</span>
								<div class="w-32">
									<div class="flex justify-between text-[10px] text-gray-500">
										<span>conf.</span>
										<span>
											{action.confidence != null ? action.confidence.toFixed(2) : '—'}
										</span>
									</div>
									<div class="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
										<div class="{bar.color} h-1.5" style="width: {bar.width}"></div>
									</div>
								</div>
							</div>
						{:else}
							<div class="text-xs text-gray-400 min-w-[140px] text-right">pending…</div>
						{/if}
					</div>
					{#if action}
						<div class="text-sm bg-gray-50 px-3 py-2 rounded whitespace-pre-wrap">
							{action.payload.comment || '(no comment)'}
						</div>
						{#if action.source_refs && action.source_refs.length > 0}
							<details class="text-xs">
								<summary class="cursor-pointer text-gray-500 hover:text-gray-700">
									{action.source_refs.length} citation{action.source_refs.length === 1 ? '' : 's'}
								</summary>
								<div class="mt-2 space-y-1 pl-4">
									{#each action.source_refs as ref}
										{@const href = getCitationHref(ref)}
										<div class="text-gray-700">
											<span class="font-mono text-gray-400">[{ref.index}]</span>
											{#if href}
												<a
													{href}
													target="_blank"
													rel="noopener"
													class="font-medium text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1"
													title="Open {ref.kind.replace(/_/g, ' ')} in a new tab"
												>
													{ref.name || ref.kind || 'passage'}
													<i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
												</a>
											{:else}
												<span class="font-medium">{ref.name || ref.kind || 'passage'}</span>
											{/if}
											<div class="text-gray-500 italic mt-0.5">{ref.snippet}</div>
										</div>
									{/each}
								</div>
							</details>
						{/if}
						{#if action.payload.status === VERDICT.NEEDS_INFO || (action.confidence != null && action.confidence < AUTO_ACCEPT_THRESHOLD)}
							<div class="flex items-center gap-3 text-xs pt-1">
								{#if retryBusyForQuestion === question.id}
									<span class="text-gray-500">
										<i class="fa-solid fa-spinner fa-spin mr-1"></i>
										Re-trying with hint…
									</span>
								{:else}
									<button
										type="button"
										class="text-blue-600 hover:text-blue-800"
										onclick={() => openPicker(question)}
										disabled={retryBusyForQuestion !== null}
									>
										<i class="fa-solid fa-link mr-1"></i>Use an existing control
									</button>
									<span class="text-gray-300">·</span>
									<button
										type="button"
										class="text-blue-600 hover:text-blue-800"
										onclick={() => openSuggest(question)}
										disabled={retryBusyForQuestion !== null}
									>
										<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>
										Suggest a control to create
									</button>
								{/if}
							</div>
						{/if}
					{/if}
				</div>
			{/each}
		</div>
	</div>
{/snippet}

{#snippet statsBreakdown()}
	<div class="bg-white shadow-sm py-4 px-6 card space-y-3">
		<div class="flex items-center justify-between gap-2">
			<div class="font-semibold text-sm">Answer breakdown</div>
			<div class="text-xs text-gray-500 text-right">
				<div>
					{answeredCount} answered{pendingCount > 0 ? ` · ${pendingCount} pending` : ''}
				</div>
				{#if answeredCount > 0}
					<div class="mt-0.5">
						<span class="text-amber-700">
							{needsReviewQuestions.filter((q) => actionByQuestion[q.id]).length} to review
						</span>
						·
						<span class="text-green-700">
							{autoAcceptedQuestions.length} auto-accepted
						</span>
					</div>
				{/if}
			</div>
		</div>

		<div class="flex w-full h-3 rounded-full overflow-hidden bg-gray-100">
			{#each statusBreakdown as item}
				{#if item.count > 0}
					<div
						class={item.color}
						style="width: {item.pct}%"
						title="{item.label}: {item.count} ({item.pct}%)"
					></div>
				{/if}
			{/each}
		</div>

		<div class="grid grid-cols-4 gap-2 text-xs">
			{#each statusBreakdown as item}
				<div class="rounded p-2 {item.pillColor}">
					<div class="font-semibold uppercase tracking-wide text-[10px]">
						{item.label}
					</div>
					<div class="flex items-baseline gap-1 mt-1">
						<span class="text-lg font-bold leading-none">{item.count}</span>
						<span class="text-[11px]">({item.pct}%)</span>
					</div>
				</div>
			{/each}
		</div>
	</div>
{/snippet}

{#snippet valueMappingHint()}
	{#if run.value_mapping?.has_multiple_vocabs}
		<div
			class="text-[11px] text-gray-500 max-w-[280px] text-right leading-snug"
			title="The questionnaire uses {run.value_mapping
				.vocab_count} different answer vocabularies — each question writes its own value."
		>
			<i class="fa-solid fa-language mr-1"></i>
			{run.value_mapping.vocab_count} answer vocabularies detected — each question writes its own value.
			<div class="text-[10px] text-gray-400 mt-0.5">
				Needs info → cell left blank for manual review.
			</div>
		</div>
	{:else if run.value_mapping && run.value_mapping.source && run.value_mapping.source !== 'fallback'}
		<div
			class="text-[11px] text-gray-500 max-w-[280px] text-right leading-snug"
			title="Yes → {run.value_mapping.yes} · Partial → {run.value_mapping.partial} · No → {run
				.value_mapping.no} · Needs info → blank for review"
		>
			<i class="fa-solid fa-language mr-1"></i>
			{#if run.value_mapping.source === 'data_validation'}
				Mapped to customer dropdown:
			{:else}
				Mapped to customer values:
			{/if}
			<span class="font-mono">{run.value_mapping.yes}</span> /
			<span class="font-mono">{run.value_mapping.partial}</span> /
			<span class="font-mono">{run.value_mapping.no}</span>
			<div class="text-[10px] text-gray-400 mt-0.5">
				Needs info → cell left blank for manual review.
			</div>
		</div>
	{:else if run.value_mapping && run.value_mapping.source === 'fallback' && run.value_mapping.candidates && run.value_mapping.candidates.length > 0}
		<div
			class="text-[11px] text-amber-600 max-w-[280px] text-right leading-snug"
			title="Customer expects: {(run.value_mapping.candidates ?? []).join(' / ')}"
		>
			<i class="fa-solid fa-triangle-exclamation mr-1"></i>
			Customer dropdown detected but mapping unavailable — answer cells will be left blank for manual
			review.
		</div>
	{:else if run.value_mapping && run.value_mapping.source === 'fallback'}
		<div class="text-[11px] text-gray-400 max-w-[280px] text-right leading-snug">
			<i class="fa-solid fa-language mr-1"></i>Using internal labels (no customer vocabulary
			detected). Needs info cells are left blank.
		</div>
	{/if}
{/snippet}
