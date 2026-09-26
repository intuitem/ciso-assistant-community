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

export interface DefaultScoreScale extends Omit<ScoreScaleValue, 'scores_definition'> {
	source: 'framework' | 'instance' | 'baseline';
	scores_definition: ScoreLevel[] | null;
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
		label: () => m.scoreScaleCapability(),
		levels: [m.scoreLevelNonExistent, ...cmmi]
	},
	{ id: '1-5', min: 1, max: 5, label: () => m.scoreScaleMaturity(), levels: cmmi },
	{
		id: '1-4',
		min: 1,
		max: 4,
		label: () => m.scoreScaleTiers(),
		levels: [
			m.scoreLevelPartial,
			m.scoreLevelRiskInformed,
			m.scoreLevelRepeatable,
			m.scoreLevelAdaptive
		]
	},
	{
		id: '0-4',
		min: 0,
		max: 4,
		label: () => m.scoreScaleImplementation(),
		levels: [
			m.scoreLevelNotImplemented,
			m.scoreLevelInitial,
			m.scoreLevelPartiallyImplemented,
			m.scoreLevelLargelyImplemented,
			m.scoreLevelFullyImplemented
		]
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
		const { preset: _preset, ...rest } = structuredClone(level ?? { score });
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
