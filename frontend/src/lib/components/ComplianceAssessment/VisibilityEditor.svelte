<script lang="ts">
	import { VISIBILITY_FIELDS, type RoleAccess } from '$lib/utils/helpers';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';

	type Pair = { auditor: RoleAccess; respondent: RoleAccess };
	type VisibilityMap = Record<string, Pair>;

	interface Props {
		value: VisibilityMap | null | undefined;
		onChange: (next: VisibilityMap) => void;
		disabled?: boolean;
		// Framework's effective_field_visibility — the complete map a new CA
		// would inherit from this framework (DEFAULT_VISIBILITY ⊕ framework's
		// own overrides, computed on the backend). Used as fallback for missing
		// keys in `value`, so pills on a fresh create form display what the
		// API will actually save.
		frameworkDefaults?: VisibilityMap | null;
	}

	let { value, onChange, disabled = false, frameworkDefaults = null }: Props = $props();

	const FIELD_LABELS: Record<string, () => string> = {
		result: m.result,
		status: m.status,
		score: m.score,
		documentation_score: m.documentationScore,
		extended_result: m.extendedResult,
		observation: m.observation,
		answers: m.answers,
		evidences: m.evidences,
		applied_controls: m.appliedControls,
		respondent_alignment: m.respondentAlignment,
		comments: m.comments
	};

	const FEATURE_FLAG_BY_FIELD: Record<string, string> = { comments: 'comments' };

	const visibleFields = $derived(
		VISIBILITY_FIELDS.filter((field) => {
			const flag = FEATURE_FLAG_BY_FIELD[field];
			return !flag || $page.data?.featureflags?.[flag];
		})
	);

	type PillValue = 'everyone' | 'auditor' | 'hidden';

	// The 3 pills the editor exposes today, each backed by a per-role pair.
	// Future PRs may add more pills (e.g. auditor_only_edit, respondent_only_edit)
	// without changing storage shape.
	const OPTIONS: { v: PillValue; label: () => string; pair: Pair; activeClass: string }[] = [
		{
			v: 'everyone',
			label: m.visibilityAuditorRespondent,
			pair: { auditor: 'edit', respondent: 'edit' },
			activeClass: 'bg-green-100 text-green-800 border-green-300'
		},
		{
			v: 'auditor',
			label: m.visibilityAuditorOnly,
			pair: { auditor: 'edit', respondent: 'hidden' },
			activeClass: 'bg-amber-100 text-amber-800 border-amber-300'
		},
		{
			v: 'hidden',
			label: m.visibilityHidden,
			pair: { auditor: 'hidden', respondent: 'hidden' },
			activeClass: 'bg-rose-100 text-rose-800 border-rose-300'
		}
	];

	function readPair(field: string): Pair {
		const raw = (value ?? {})[field] as any;
		if (raw && typeof raw === 'object') {
			return {
				auditor: (raw.auditor as RoleAccess) ?? 'edit',
				respondent: (raw.respondent as RoleAccess) ?? 'edit'
			};
		}
		// No explicit override yet (e.g. fresh create form). Fall back to the
		// framework's effective_field_visibility — the complete map the backend
		// will use as the base when seeding the new CA's field_visibility.
		const fallback = frameworkDefaults?.[field];
		if (fallback && typeof fallback === 'object') {
			return {
				auditor: (fallback.auditor as RoleAccess) ?? 'edit',
				respondent: (fallback.respondent as RoleAccess) ?? 'edit'
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

	// Per-field constraint: a child field's visibility cannot exceed its parent's.
	// Extends naturally if more parent/child relationships are added.
	const PARENT_OF: Record<string, string> = {
		documentation_score: 'score',
		extended_result: 'result'
	};

	// Per-field pill exclusions: pills that don't make semantic sense for a given
	// field. respondent_alignment with AUDITOR_ONLY is incoherent — the field is
	// only ever populated by the respondent answering the auto-question, so
	// auditor-only would prevent it from being filled in at all.
	const DISALLOWED_PILLS: Record<string, PillValue[]> = {
		respondent_alignment: ['auditor']
	};

	function isOptionAllowed(field: string, optionValue: PillValue): boolean {
		if (DISALLOWED_PILLS[field]?.includes(optionValue)) return false;
		const parent = PARENT_OF[field];
		if (!parent) return true;
		const parentPill = pillFor(parent);
		if (parentPill === null) return true; // unknown future shape — don't constrain
		return VISIBILITY_RANK[optionValue] <= VISIBILITY_RANK[parentPill];
	}

	// Children that should be clamped down whenever their parent's permissiveness drops.
	const CHILDREN_OF: Record<string, string[]> = {
		score: ['documentation_score'],
		result: ['extended_result']
	};

	function setVisibility(field: string, pill: PillValue) {
		const target = OPTIONS.find((o) => o.v === pill);
		if (!target) return;
		const next: VisibilityMap = { ...value };
		next[field] = { ...target.pair };
		// is_scored has no independent meaning — it always tracks score
		if (field === 'score') {
			next['is_scored'] = { ...target.pair };
		}
		// Clamp any child fields that would now exceed the parent's permissiveness.
		for (const child of CHILDREN_OF[field] ?? []) {
			const childPill = pairToPill(readPair(child));
			if (childPill !== null && VISIBILITY_RANK[childPill] > VISIBILITY_RANK[pill]) {
				next[child] = { ...target.pair };
			}
		}
		onChange(next);
	}
</script>

<div class="space-y-1">
	<h3 class="font-semibold text-sm">{m.fieldVisibility()}</h3>
	<p class="text-xs text-gray-500 mb-2">{m.fieldVisibilityHelpText()}</p>
	<div class="max-w-xl">
		{#each visibleFields as field}
			{@const pill = pillFor(field)}
			{@const label = FIELD_LABELS[field]?.() ?? field}
			<div class="flex items-center justify-between gap-3 py-1">
				<span class="text-sm text-gray-700">{label}</span>
				<div
					class="inline-flex shrink-0 rounded-md border border-gray-200 bg-gray-50 p-0.5"
					role="radiogroup"
					aria-label={label}
				>
					{#each OPTIONS as option}
						{@const optionDisabled = disabled || !isOptionAllowed(field, option.v)}
						<button
							type="button"
							role="radio"
							aria-checked={pill === option.v}
							disabled={optionDisabled}
							data-testid={`visibility-${field}-${option.v}`}
							onclick={() => setVisibility(field, option.v)}
							class="px-2.5 py-0.5 text-xs font-medium rounded border transition-colors disabled:opacity-50 disabled:cursor-not-allowed {pill ===
							option.v
								? `${option.activeClass} shadow-sm`
								: 'text-gray-600 hover:text-gray-900 border-transparent'}"
						>
							{option.label()}
						</button>
					{/each}
				</div>
			</div>
		{/each}
	</div>
</div>
