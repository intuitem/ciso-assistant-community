import { URL_MODEL_MAP } from './crud';

export const getModelName = (event: string): string | null => {
	if (typeof event !== 'string' || !event.includes('.')) {
		console.warn('Skipping event with invalid value:', event);
		return null;
	}
	return event.split('.')[0];
};

export const eventsByModel = (events: string[]) => {
	return events.reduce((acc: Record<string, string[]>, event) => {
		const modelName = getModelName(event);
		if (modelName) {
			(acc[modelName] = acc[modelName] || []).push(event);
		}
		return acc;
	}, {});
};

export const modelEventsMap = (events: string[]) =>
	Object.values(URL_MODEL_MAP).reduce((acc: Record<string, any>, model) => {
		if (!model?.name) {
			console.warn('Skipping model with no name:', model);
			return acc;
		}
		if (acc?.[model.name]) {
			// skip duplicates (e.g. policies)
			return acc;
		}
		acc[model.name] = {
			i18nName: model.localName,
			events: eventsByModel(events)[model.name] || []
		};
		return acc;
	}, {});
