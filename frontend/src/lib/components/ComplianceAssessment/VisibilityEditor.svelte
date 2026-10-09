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
		task_templates: m.taskTemplates,
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

	type Role = keyof Pair;
	const ROLES: { role: Role; label: () => string }[] = [
		{ role: 'auditor', label: m.visibilityRoleAuditor },
		{ role: 'respondent', label: m.visibilityRoleRespondent }
	];

	// Each role picks its own access level, so read and write can be granted separately.
	const OPTIONS: { v: RoleAccess; label: () => string; activeClass: string }[] = [
		{
			v: 'edit',
			label: m.visibilityEdit,
			activeClass: 'bg-green-100 text-green-800 border-green-300'
		},
		{
			v: 'read',
			label: m.visibilityRead,
			activeClass: 'bg-sky-100 text-sky-800 border-sky-300'
		},
		{
			v: 'hidden',
			label: m.visibilityHidden,
			activeClass: 'bg-rose-100 text-rose-800 border-rose-300'
		}
	];

	// Reads from `map` so a pending update can see the fields it already changed.
	function readPair(field: string, map: VisibilityMap | null | undefined = value): Pair {
		const raw = (map ?? {})[field] as any;
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

	const ACCESS_RANK: Record<RoleAccess, number> = { hidden: 0, read: 1, edit: 2 };

	// Per-field constraint: for each role, a child field's access cannot exceed its parent's.
	// Extends naturally if more parent/child relationships are added.
	const PARENT_OF: Record<string, string> = {
		documentation_score: 'score',
		extended_result: 'result'
	};

	// Children that should be clamped down whenever their parent's access drops.
	const CHILDREN_OF: Record<string, string[]> = {
		score: ['documentation_score'],
		result: ['extended_result']
	};

	// Fields whose value can be computed from the answers: nobody needs to write them,
	// so read-only combinations make sense there.
	const COMPUTABLE_FIELDS = new Set(['score', 'result']);

	// respondent_alignment is only ever populated by the respondent answering the
	// auto-question: showing it to the auditor while hiding it from the respondent
	// would leave it empty forever.
	function isAlignmentIncoherent(field: string, pair: Pair): boolean {
		return (
			field === 'respondent_alignment' && pair.respondent === 'hidden' && pair.auditor !== 'hidden'
		);
	}

	function isValidPair(field: string, pair: Pair): boolean {
		// The auditor sees at least what the respondent sees.
		if (pair.auditor === 'hidden' && pair.respondent !== 'hidden') return false;
		if (isAlignmentIncoherent(field, pair)) return false;
		if (pair.auditor === 'hidden' && pair.respondent === 'hidden') return true;
		// A visible field needs a writer, unless its value is computed.
		return pair.auditor === 'edit' || pair.respondent === 'edit' || COMPUTABLE_FIELDS.has(field);
	}

	// A role may never exceed the parent field's access for that role.
	function withinParent(
		field: string,
		role: Role,
		access: RoleAccess,
		map: VisibilityMap | null | undefined = value
	): boolean {
		const parent = PARENT_OF[field];
		return !parent || ACCESS_RANK[access] <= ACCESS_RANK[readPair(parent, map)[role]];
	}

	// The auditor's choice drives the field: the respondent is offered only what fits it.
	function respondentOptions(
		field: string,
		auditor: RoleAccess,
		map: VisibilityMap | null | undefined = value
	): RoleAccess[] {
		return (['hidden', 'read', 'edit'] as RoleAccess[]).filter(
			(respondent) =>
				isValidPair(field, { auditor, respondent }) &&
				withinParent(field, 'respondent', respondent, map)
		);
	}

	// Keep the respondent's access when it still fits, else take the most restrictive one that does.
	function fitPair(
		field: string,
		auditor: RoleAccess,
		respondent: RoleAccess,
		map: VisibilityMap
	): Pair {
		const options = respondentOptions(field, auditor, map);
		if (options.includes(respondent)) return { auditor, respondent };
		if (options.length) return { auditor, respondent: options[0] };
		return { auditor: 'hidden', respondent: 'hidden' };
	}

	function isOptionAllowed(field: string, role: Role, access: RoleAccess): boolean {
		if (role === 'auditor') return withinParent(field, 'auditor', access);
		return respondentOptions(field, readPair(field).auditor).includes(access);
	}

	function setAccess(field: string, role: Role, access: RoleAccess) {
		const next: VisibilityMap = { ...value };
		const current = readPair(field);
		const pair =
			role === 'auditor'
				? fitPair(field, access, current.respondent, next)
				: { ...current, respondent: access };
		next[field] = pair;
		// is_scored has no independent meaning — it always tracks score
		if (field === 'score') {
			next['is_scored'] = { ...pair };
		}
		// Clamp child fields down to the parent's new access, then refit their respondent.
		for (const child of CHILDREN_OF[field] ?? []) {
			const childPair = readPair(child, next);
			const auditor =
				ACCESS_RANK[childPair.auditor] > ACCESS_RANK[pair.auditor]
					? pair.auditor
					: childPair.auditor;
			next[child] = fitPair(child, auditor, childPair.respondent, next);
		}
		onChange(next);
	}
</script>

<div class="space-y-1">
	<h3 class="font-semibold text-sm">{m.fieldVisibility()}</h3>
	<p class="text-xs text-surface-600-400 mb-2">{m.fieldVisibilityHelpText()}</p>
	<div class="grid grid-cols-[1fr_auto_auto] items-center gap-x-3 gap-y-1 max-w-2xl">
		<span></span>
		{#each ROLES as { label }}
			<span class="text-xs font-semibold text-surface-600-400 text-center">{label()}</span>
		{/each}
		{#each visibleFields as field}
			{@const pair = readPair(field)}
			{@const label = FIELD_LABELS[field]?.() ?? field}
			<span class="text-sm text-surface-700-300">{label}</span>
			{#each ROLES as { role, label: roleLabel }}
				<div
					class="inline-flex shrink-0 rounded-md border border-surface-200-800 bg-surface-50-950 p-0.5"
					role="radiogroup"
					aria-label={`${label} — ${roleLabel()}`}
				>
					{#each OPTIONS as option}
						{@const optionDisabled = disabled || !isOptionAllowed(field, role, option.v)}
						<button
							type="button"
							role="radio"
							aria-checked={pair[role] === option.v}
							disabled={optionDisabled}
							data-testid={`visibility-${field}-${role}-${option.v}`}
							onclick={() => setAccess(field, role, option.v)}
							class="px-2.5 py-0.5 text-xs font-medium rounded border transition-colors disabled:opacity-50 disabled:cursor-not-allowed {pair[
								role
							] === option.v
								? `${option.activeClass} shadow-sm`
								: 'text-surface-600-400 hover:text-surface-900-100 border-transparent'}"
						>
							{option.label()}
						</button>
					{/each}
				</div>
			{/each}
		{/each}
	</div>
</div>
