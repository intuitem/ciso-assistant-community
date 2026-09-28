import * as m from '$paraglide/messages';
import type { locales } from '$paraglide/runtime';

type Locale = (typeof locales)[number];
type LevelMessage = (inputs?: Record<string, never>, options?: { locale?: Locale }) => string;

export type ScoreLevelField = 'name' | 'description' | 'description_doc';

export type ScoreLevelText = Partial<Record<ScoreLevelField, string>>;

export interface ScoreLevel {
	score: number;
	name?: string | null;
	description?: string | null;
	description_doc?: string | null;
	preset?: string | null;
	translations?: Record<string, ScoreLevelText>;
}

export interface ScoreScaleValue {
	score_scale_preset: string | null;
	min_score: number;
	max_score: number;
	scores_definition: ScoreLevel[];
}

export interface ScoreScalePreset {
	id: string;
	min: number;
	max: number;
	label: () => string;
	levels: LevelMessage[];
}

const cmmi: LevelMessage[] = [
	m.scoreLevelInitial,
	m.scoreLevelManaged,
	m.scoreLevelDefined,
	m.scoreLevelQuantitativelyManaged,
	m.scoreLevelOptimized
];

// A preset's range is frozen: rewording is free, a new range needs a new id.
export const SCORE_SCALE_PRESETS: ScoreScalePreset[] = [
	{ id: '0-100', min: 0, max: 100, label: () => m.percentage(), levels: [] },
	{
		id: '0-5',
		min: 0,
		max: 5,
		label: () => m.scoreScale0to5(),
		levels: [
			m.scoreLevelIncomplete,
			m.scoreLevelPerformed,
			m.scoreLevelManaged,
			m.scoreLevelEstablished,
			m.scoreLevelPredictable,
			m.scoreLevelInnovating
		]
	},
	{ id: '1-5', min: 1, max: 5, label: () => m.scoreScale1to5(), levels: cmmi },
	{
		id: '1-4',
		min: 1,
		max: 4,
		label: () => m.scoreScale1to4(),
		levels: [
			m.scoreLevelPartial,
			m.scoreLevelRiskInformed,
			m.scoreLevelRepeatable,
			m.scoreLevelAdaptive
		]
	},
	{
		id: '0-3',
		min: 0,
		max: 3,
		label: () => m.scoreScale0to3(),
		levels: [m.scoreLevelIncomplete, m.scoreLevelInitial, m.scoreLevelManaged, m.scoreLevelDefined]
	}
];

export const MAX_LABELLED_LEVELS = 11;

// Stored scales are either a bare list or wrapped as {scale, alternatives}.
export function scaleLevels(definition: unknown): ScoreLevel[] {
	if (Array.isArray(definition)) return definition;
	const scale = (definition as { scale?: unknown } | null)?.scale;
	return Array.isArray(scale) ? scale : [];
}

export function getPreset(id?: string | null) {
	return SCORE_SCALE_PRESETS.find((p) => p.id === id);
}

export function hasLabelledLevels(min: number, max: number) {
	return max > min && max - min + 1 <= MAX_LABELLED_LEVELS;
}

export function presetLevelName(preset: ScoreScalePreset, score: number, locale: string) {
	return preset.levels[score - preset.min]?.({}, { locale: locale as Locale });
}

export function localizedLevelField(
	level: ScoreLevel,
	field: ScoreLevelField,
	locale: string
): string | undefined {
	const own = level.translations?.[locale]?.[field];
	if (own) return own;
	const preset = field === 'name' ? getPreset(level.preset) : undefined;
	return (preset && presetLevelName(preset, level.score, locale)) || level[field] || undefined;
}

// Rebuild a full level list for editing, keeping every other level field
// (description, description_doc, …) and resolving names in each language.
export function seedLevels(
	source: ScoreLevel[],
	sourcePreset: ScoreScalePreset | undefined,
	lo: number,
	hi: number,
	languages: string[]
): ScoreLevel[] {
	if (!hasLabelledLevels(lo, hi)) return [];
	return Array.from({ length: hi - lo + 1 }, (_, i) => lo + i).map((score) => {
		const level = source.find((l) => l.score === score);
		// JSON copy: callers may hand over Svelte proxies, which structuredClone rejects.
		const { preset: _preset, ...rest }: ScoreLevel = JSON.parse(JSON.stringify(level ?? { score }));
		const translations = rest.translations ?? {};
		for (const loc of languages) {
			const name = resolveLevelName(level, sourcePreset, score, loc);
			if (name) translations[loc] = { ...translations[loc], name };
		}
		return {
			...rest,
			score,
			name: level?.name ?? translations[languages[0]]?.name ?? '',
			translations
		};
	});
}

export function resolveLevelName(
	level: ScoreLevel | undefined,
	preset: ScoreScalePreset | undefined,
	score: number,
	locale: string
): string {
	const own = level?.translations?.[locale]?.name;
	if (own) return own;
	if (preset) return presetLevelName(preset, score, locale) ?? '';
	return level?.name ?? '';
}

// ---------------------------------------------------------------------------
// Audit scale picker: the framework's scale, the organisation's, a preset, or
// (for copies) the baseline audit's.
// ---------------------------------------------------------------------------

export type ScaleOptionSource = 'framework' | 'organisation' | 'preset' | 'baseline' | 'current';

export interface ScaleOption {
	id: string;
	source: ScaleOptionSource;
	min: number;
	max: number;
	preset: ScoreScalePreset | undefined;
	levels: ScoreLevel[];
	// What the form sends; null lets the backend copy the framework's scale.
	value: ScoreScaleValue | null;
}

export interface FrameworkScale {
	min_score?: number | null;
	max_score?: number | null;
	scores_definition?: unknown;
	is_scale_bound?: boolean;
}

export interface ScaleOptionsInput {
	framework: FrameworkScale | null;
	organisation?: ScoreScaleValue | null;
	baseline?: ScoreScaleValue | null;
	// The scale an existing audit already has (edit form).
	current?: ScoreScaleValue | null;
}

function fromValue(id: string, source: ScaleOptionSource, value: ScoreScaleValue): ScaleOption {
	const levels = scaleLevels(value.scores_definition);
	return {
		id,
		source,
		min: value.min_score,
		max: value.max_score,
		preset: getPreset(value.score_scale_preset),
		levels,
		value: { ...value, scores_definition: levels }
	};
}

const sameLevels = (a: unknown, b: unknown) =>
	JSON.stringify(scaleLevels(a)) === JSON.stringify(scaleLevels(b));

function matches(option: ScaleOption, current: ScoreScaleValue): boolean {
	const unlabelled = !current.score_scale_preset && !scaleLevels(current.scores_definition).length;
	if (option.preset)
		return (
			current.score_scale_preset === option.preset.id ||
			// Audits predating presets, on a range whose preset has no labels (0-100).
			(unlabelled &&
				!option.preset.levels.length &&
				current.min_score === option.min &&
				current.max_score === option.max)
		);
	return (
		!current.score_scale_preset &&
		current.min_score === option.min &&
		current.max_score === option.max &&
		sameLevels(current.scores_definition, option.levels)
	);
}

export function frameworkDeclaresScale(framework: FrameworkScale | null): boolean {
	if (!framework) return false;
	return (
		scaleLevels(framework.scores_definition).length > 0 ||
		(framework.min_score ?? 0) !== 0 ||
		(framework.max_score ?? 100) !== 100
	);
}

export function scaleOptions({ framework, organisation, baseline, current }: ScaleOptionsInput): {
	options: ScaleOption[];
	selected: string;
} {
	const options: ScaleOption[] = [];
	const bound = Boolean(framework?.is_scale_bound);
	// A framework without a scale of its own only carries the 0-100 model default.
	if (framework && (bound || frameworkDeclaresScale(framework))) {
		options.push({
			id: 'framework',
			source: 'framework',
			min: framework.min_score ?? 0,
			max: framework.max_score ?? 100,
			preset: undefined,
			levels: scaleLevels(framework.scores_definition),
			value: null
		});
	}
	if (!bound) {
		if (baseline) options.push(fromValue('baseline', 'baseline', baseline));
		if (organisation) options.push(fromValue('organisation', 'organisation', organisation));
		for (const preset of SCORE_SCALE_PRESETS) {
			// The organisation option already stands for its own preset.
			if (preset.id === organisation?.score_scale_preset) continue;
			options.push(
				fromValue(preset.id, 'preset', {
					score_scale_preset: preset.id,
					min_score: preset.min,
					max_score: preset.max,
					scores_definition: []
				})
			);
		}
	}

	if (current) {
		const match = options.find(
			(option) => option.source !== 'baseline' && matches(option, current)
		);
		if (match) return { options, selected: match.id };
		options.unshift(fromValue('current', 'current', current));
		return { options, selected: 'current' };
	}
	if (bound) return { options, selected: 'framework' };
	if (baseline) return { options, selected: 'baseline' };
	if (options.some((o) => o.id === 'framework')) return { options, selected: 'framework' };
	return { options, selected: organisation ? 'organisation' : '0-100' };
}

// Labels to show for an option, in the viewer's language.
export function previewLevels(
	option: Pick<ScaleOption, 'min' | 'max' | 'preset' | 'levels'>,
	locale: string
): { score: number; name: string }[] {
	if (option.preset && hasLabelledLevels(option.min, option.max)) {
		return Array.from({ length: option.max - option.min + 1 }, (_, i) => option.min + i).map(
			(score) => ({
				score,
				name:
					localizedLevelField(
						{ ...option.levels.find((l) => l.score === score), score, preset: option.preset!.id },
						'name',
						locale
					) ?? ''
			})
		);
	}
	return option.levels
		.map((level) => ({
			score: level.score,
			name: localizedLevelField(level, 'name', locale) ?? ''
		}))
		.filter((level) => level.name);
}
