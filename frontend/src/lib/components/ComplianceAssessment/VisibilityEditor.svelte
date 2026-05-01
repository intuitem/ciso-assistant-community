<script lang="ts">
	import { VISIBILITY_FIELDS, type RoleAccess } from '$lib/utils/helpers';
	import { page } from '$app/stores';
	import type { SuperForm } from 'sveltekit-superforms';

	interface Props {
		form: SuperForm<any>;
		disabled?: boolean;
	}

	let { form, disabled = false }: Props = $props();

	const FIELD_LABELS: Record<string, string> = {
		result: 'Result',
		status: 'Status',
		score: 'Score',
		documentation_score: 'Documentation score',
		extended_result: 'Extended result',
		observation: 'Observation',
		answers: 'Answers',
		evidences: 'Evidences',
		applied_controls: 'Applied controls',
		respondent_alignment: 'Respondent alignment',
		comments: 'Comments'
	};

	const FEATURE_FLAG_BY_FIELD: Record<string, string> = { comments: 'comments' };

	const visibleFields = $derived(
		VISIBILITY_FIELDS.filter((field) => {
			const flag = FEATURE_FLAG_BY_FIELD[field];
			return !flag || $page.data?.featureflags?.[flag];
		})
	);

	type Pair = { auditor: RoleAccess; respondent: RoleAccess };
	type PillValue = 'everyone' | 'auditor' | 'hidden';

	// The 3 pills the editor exposes today, each backed by a per-role pair.
	// Future PRs may add more pills (e.g. auditor_only_edit, respondent_only_edit)
	// without changing storage shape.
	const OPTIONS: { v: PillValue; label: string; pair: Pair; activeClass: string }[] = [
		{
			v: 'everyone',
			label: 'Auditor + Respondent',
			pair: { auditor: 'edit', respondent: 'edit' },
			activeClass: 'bg-green-100 text-green-800 border-green-300'
		},
		{
			v: 'auditor',
			label: 'Auditor only',
			pair: { auditor: 'edit', respondent: 'hidden' },
			activeClass: 'bg-amber-100 text-amber-800 border-amber-300'
		},
		{
			v: 'hidden',
			label: 'Hidden',
			pair: { auditor: 'hidden', respondent: 'hidden' },
			activeClass: 'bg-rose-100 text-rose-800 border-rose-300'
		}
	];

	const formData = form.form;

	function readPair(field: string): Pair {
		const raw = ($formData.field_visibility as Record<string, any> | undefined)?.[field];
		if (raw && typeof raw === 'object') {
			return {
				auditor: (raw.auditor as RoleAccess) ?? 'edit',
				respondent: (raw.respondent as RoleAccess) ?? 'edit'
			};
		}
		return { auditor: 'edit', respondent: 'edit' };
	}

	function pairToPill(pair: Pair): PillValue | null {
		const match = OPTIONS.find(
			(o) => o.pair.auditor === pair.auditor && o.pair.respondent === pair.respondent
		);
		return match ? match.v : null;
	}

	const VISIBILITY_RANK: Record<PillValue, number> = { hidden: 0, auditor: 1, everyone: 2 };

	function pillFor(field: string): PillValue | null {
		return pairToPill(readPair(field));
	}

	function isOptionAllowed(field: string, optionValue: PillValue): boolean {
		// Documentation score visibility cannot exceed implementation score visibility.
		if (field === 'documentation_score') {
			const scorePill = pillFor('score');
			if (scorePill === null) return true; // unknown future shape — don't constrain
			return VISIBILITY_RANK[optionValue] <= VISIBILITY_RANK[scorePill];
		}
		return true;
	}

	function setVisibility(field: string, pill: PillValue) {
		const target = OPTIONS.find((o) => o.v === pill);
		if (!target) return;
		formData.update((data) => {
			const current = { ...((data.field_visibility as Record<string, Pair>) ?? {}) };
			const writePair = (key: string, p: Pair) => {
				current[key] = { ...p };
			};
			writePair(field, target.pair);
			// is_scored has no independent meaning — it always tracks score
			if (field === 'score') {
				writePair('is_scored', target.pair);
				// Documentation score cannot exceed score's permissiveness; clamp down.
				const docPill = pillFor('documentation_score');
				if (docPill !== null && VISIBILITY_RANK[docPill] > VISIBILITY_RANK[pill]) {
					writePair('documentation_score', target.pair);
				}
			}
			return { ...data, field_visibility: current };
		});
	}
</script>

<div class="space-y-1">
	<h3 class="font-semibold text-sm">Field visibility</h3>
	<p class="text-xs text-gray-500 mb-2">
		Control which assessment fields each viewer role can see and edit.
	</p>
	<div class="max-w-xl">
		{#each visibleFields as field}
			{@const pill = pillFor(field)}
			<div class="flex items-center justify-between gap-3 py-1">
				<span class="text-sm text-gray-700">{FIELD_LABELS[field] ?? field}</span>
				<div
					class="inline-flex shrink-0 rounded-md border border-gray-200 bg-gray-50 p-0.5"
					role="radiogroup"
					aria-label={FIELD_LABELS[field] ?? field}
				>
					{#each OPTIONS as option}
						{@const optionDisabled = disabled || !isOptionAllowed(field, option.v)}
						<button
							type="button"
							role="radio"
							aria-checked={pill === option.v}
							disabled={optionDisabled}
							onclick={() => setVisibility(field, option.v)}
							class="px-2.5 py-0.5 text-xs font-medium rounded border transition-colors disabled:opacity-50 disabled:cursor-not-allowed {pill ===
							option.v
								? `${option.activeClass} shadow-sm`
								: 'text-gray-600 hover:text-gray-900 border-transparent'}"
						>
							{option.label}
						</button>
					{/each}
				</div>
			</div>
		{/each}
	</div>
</div>
