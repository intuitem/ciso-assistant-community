import { URL_MODEL_MAP } from '$lib/utils/crud';
import { MODEL_MAP_OVERRIDE } from '$lib/utils/models';

export function routeToModelInfo(model: string) {
	const baseModel = model.split('_')[0];
	const map = URL_MODEL_MAP[model] || URL_MODEL_MAP[baseModel] || {};
	// The urlmodel of {model}_duplicate must be {model}
	map['urlModel'] = baseModel;
  const override = MODEL_MAP_OVERRIDE[baseModel] || {};
	return {...map, ...override};
}
