<script lang="ts">
	import { VISIBILITY_FIELDS } from '$lib/utils/helpers';
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

	// Fields gated by a global feature flag — hidden from the editor when the flag is off.
	const FF_GATED: Record<string, string> = {
		comments: 'comments'
	};

	const visibleFields = $derived(
		VISIBILITY_FIELDS.filter((field) => {
			const flag = FF_GATED[field];
			return !flag || $page.data?.featureflags?.[flag];
		})
	);

	const OPTIONS = [
		{
			v: 'everyone',
			label: 'Auditor + Respondent',
			activeClass: 'bg-green-100 text-green-800 border-green-300'
		},
		{
			v: 'auditor',
			label: 'Auditor only',
			activeClass: 'bg-amber-100 text-amber-800 border-amber-300'
		},
		{
			v: 'hidden',
			label: 'Hidden',
			activeClass: 'bg-rose-100 text-rose-800 border-rose-300'
		}
	] as const;

	const formData = form.form;

	function visibilityFor(field: string): string {
		return (
			($formData.field_visibility as Record<string, string> | undefined)?.[field] ?? 'everyone'
		);
	}

	const VISIBILITY_RANK: Record<string, number> = { hidden: 0, auditor: 1, everyone: 2 };

	function isOptionAllowed(field: string, optionValue: string): boolean {
		// Documentation score visibility cannot exceed implementation score visibility.
		if (field === 'documentation_score') {
			return VISIBILITY_RANK[optionValue] <= VISIBILITY_RANK[visibilityFor('score')];
		}
		return true;
	}

	function setVisibility(field: string, value: string) {
		formData.update((data) => {
			const current = { ...((data.field_visibility as Record<string, string>) ?? {}) };
			const set = (key: string, v: string) => {
				if (v === 'everyone') {
					delete current[key];
				} else {
					current[key] = v;
				}
			};
			set(field, value);
			// is_scored has no independent meaning — it always tracks score
			if (field === 'score') {
				set('is_scored', value);
				// Documentation score visibility cannot exceed score's; clamp it down.
				const docCurrent = current['documentation_score'] ?? 'everyone';
				if (VISIBILITY_RANK[docCurrent] > VISIBILITY_RANK[value]) {
					set('documentation_score', value);
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
			{@const value = visibilityFor(field)}
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
							aria-checked={value === option.v}
							disabled={optionDisabled}
							onclick={() => setVisibility(field, option.v)}
							class="px-2.5 py-0.5 text-xs font-medium rounded border transition-colors disabled:opacity-50 disabled:cursor-not-allowed {value ===
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
