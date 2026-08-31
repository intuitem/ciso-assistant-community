/**
 * Icon rendering for actor pickers (AutocompleteSelect optionsInfoFields
 * iconMap): a fixed-width glyph replaces the text type prefix so names align
 * and labels don't blow up in translation — the translated type becomes the
 * tooltip. Icons follow the sidebar vocabulary; third parties get a distinct
 * glyph and a warning tint so external actors stand out in assignment lists.
 */
export const ACTOR_TYPE_ICON_MAP: Record<string, string> = {
	user: 'fa-solid fa-user text-primary-600-400',
	team: 'fa-solid fa-people-group text-primary-600-400',
	internalEntity: 'fa-solid fa-building text-primary-600-400',
	externalEntity: 'fa-solid fa-building-circle-arrow-right text-warning-600-400'
};
