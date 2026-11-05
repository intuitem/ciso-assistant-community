import { defineParams } from '@sveltejs/kit/params';
// .ts extensions and no $app/* or .svelte in this graph: `vite build` imports this file
// with plain Node (sveltejs/kit#17442)
import { isLocale } from '#paraglide/runtime.js';
import { FIELD_KEYS, FILTER_KEYS } from '#lib/utils/param-keys.ts';
import {
	THIRD_PARTY_URL_MODEL,
	type thirdPartyUrlModel,
	URL_MODEL,
	type urlModel
} from '#lib/utils/types.ts';

const URN_REGEX =
	/^urn:([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)(?::([a-zA-Z0-9_-]+))?:([0-9A-Za-z\[\]\(\)\-\._:]+)$/;

const normalize = (param: string) => param.toLowerCase().replace(/-/g, '_');

const matchFields = (param: string) => FIELD_KEYS.has(normalize(param));

const matchFilters = (param: string) => FILTER_KEYS.has(normalize(param));

const matchIntegration_field = (param: string) => {
	const fields = ['configs', 'remote_objects'];

	return fields.includes(param.toLowerCase().replace(/-/g, '_'));
};

const matchLang = isLocale;

const models = THIRD_PARTY_URL_MODEL;

const matchThirdparty_urlmodels = (param: string) => {
	return models.includes(param as thirdPartyUrlModel);
};

const models2 = URL_MODEL;

const matchUrlmodel = (param: string) => {
	return models2.includes(param as urlModel);
};

const matchUrn = (param: string) => {
	return URN_REGEX.test(param);
};

export const matchUuid = (param: string) => {
	return /^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$/.test(
		param
	);
};

export const params = defineParams({
	fields: (param) => (matchFields(param) ? param : undefined),
	filters: (param) => (matchFilters(param) ? param : undefined),
	integration_field: (param) => (matchIntegration_field(param) ? param : undefined),
	lang: (param) => (matchLang(param) ? param : undefined),
	thirdparty_urlmodels: (param) => (matchThirdparty_urlmodels(param) ? param : undefined),
	urlmodel: (param) => (matchUrlmodel(param) ? param : undefined),
	urn: (param) => (matchUrn(param) ? param : undefined),
	uuid: (param) => (matchUuid(param) ? param : undefined)
});
