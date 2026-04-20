import { error } from '@sveltejs/kit';
import type { RequestHandler, NumericRange } from '@sveltejs/kit';

import { BASE_API_URL } from '$lib/utils/constants';
import { getModelInfo } from '$lib/utils/crud';

import type { urlModel, thirdPartyUrlModel } from '$lib/utils/types';

interface BaseParams {
	/** Required by the `RequestHandler` type to treat params as a string dictionary. */
	[key: string]: string;
}

/** Parameters for `(app)/(internal)/[model=urlmodel]/[id=uuid]/+server.ts` API routes. */
interface ParamsUrlmodel extends BaseParams {
	model: urlModel;
}

/** Parameters for `(app)/(internal)/[model=urlmodel]/[id=uuid]/+server.ts` API routes. */
interface ParamsUrlmodelId extends ParamsUrlmodel {
	id: string;
}

/** Parameters for `(app)/(internal)/[model=urlmodel]/[id=uuid]/[field=fields]/+server.ts` API routes. */
interface ParamsUrlmodelIdField extends ParamsUrlmodelId {
	field: string;
}

/** Parameters for `(app)/(internal)/[model=thirdparty_urlmodels]/[id=uuid]/+server.ts` API routes. */
interface ParamsThirdPartyUrlmodelId extends BaseParams {
	model: thirdPartyUrlModel;
	id: string;
}

export const urlmodelIdGET: RequestHandler<ParamsUrlmodelId> = async ({ fetch, params, url }) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/${
		url.searchParams.size > 0 ? '?' + url.searchParams.toString() : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

/** Generic `GET` request handler for any API routes matching `(app)/(internal)/[model=urlmodel]/[id=uuid]/+server.ts`.
 *
 * Example for `(app)/(internal)/accreditations/[id=uuid]/+server.ts`:
 *
 * ```ts
 * export const GET = genericUrlmodelIdGET("accreditations");
 * ```
 */
export function genericUrlmodelIdGET(urlModel: urlModel): typeof urlmodelIdGET {
	return async (event) =>
		urlmodelIdGET({
			...event,
			params: { ...event.params, model: urlModel }
		});
}

export const urlmodelIdPATCH: RequestHandler<ParamsUrlmodelId> = async ({
	fetch,
	params,
	request
}) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/`;

	const body = await request.json();
	const res = await fetch(endpoint, {
		method: 'PATCH',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body)
	});

	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}

	const data = await res.json();
	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

/** Generic `PATCH` request handler for any API routes matching `(app)/(internal)/[model=urlmodel]/[id=uuid]/+server.ts`.
 *
 * Example for `(app)/(internal)/accreditations/[id=uuid]/+server.ts`:
 *
 * ```ts
 * export const PATCH = genericUrlmodelIdPATCH("accreditations");
 * ```
 */
export function genericUrlmodelIdPATCH(urlModel: urlModel): typeof urlmodelIdPATCH {
	return async (event) =>
		urlmodelIdPATCH({
			...event,
			params: { ...event.params, model: urlModel }
		});
}

export const urlmodelGET: RequestHandler<ParamsUrlmodel> = async ({ fetch, params, url }) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ? model.endpointUrl : params.model}/${
		url.searchParams ? '?' + url.searchParams.toString() : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

/** Generic `GET` request handler for any API routes matching `(app)/(internal)/[model=urlmodel]/+server.ts`.
 *
 * Example for `(app)/(internal)/risk-scenarios/+server.ts`:
 *
 * ```ts
 * export const GET = genericUrlmodelGET("risk-scenarios");
 * ```
 */
export function genericUrlmodelGET(urlModel: urlModel): typeof urlmodelGET {
	return async (event) =>
		urlmodelGET({
			...event,
			params: { ...event.params, model: urlModel }
		});
}

export const thirdPartyUrlmodelGET: RequestHandler<ParamsThirdPartyUrlmodelId> = async ({
	fetch,
	params,
	url
}) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ? model.endpointUrl : params.model}/${
		url.searchParams ? '?' + url.searchParams.toString() : ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

/** Generic `GET` request handler for any API routes matching `(app)/(internal)/[model=thirdparty_urlmodels]/[id=uuid]/+server.ts`.
 *
 * Example for `(app)/(third-party)/evidences/[id=uuid]/+server.ts`:
 *
 * ```ts
 * export const GET = genericThirdPartyUrlmodelGET("evidences");
 * ```
 */
export function genericThirdPartyUrlmodelGET(
	urlModel: thirdPartyUrlModel
): typeof thirdPartyUrlmodelGET {
	return async (event) =>
		thirdPartyUrlmodelGET({
			...event,
			params: { ...event.params, model: urlModel }
		});
}

export const urlmodelIdFieldGET: RequestHandler<ParamsUrlmodelIdField> = async ({
	fetch,
	params,
	url
}) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/${params.field}/${
		url.search || ''
	}`;

	const res = await fetch(endpoint);
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

/** Generic `GET` request handler for any API routes matching `(app)/(internal)/[model=urlmodel]/[id=uuid]/[field=fields]/+server.ts`.
 *
 * Example for `(app)/(internal)/asset-assessments/[id=uuid]/dependencies/+server.ts`:
 *
 * ```ts
 * export const GET = genericUrlmodelIdFieldGET("asset-assessments", "dependencies");
 * ```
 */
export function genericUrlmodelIdFieldGET(
	urlModel: urlModel,
	field: string
): typeof urlmodelIdFieldGET {
	return async (event) =>
		urlmodelIdFieldGET({
			...event,
			params: { ...event.params, model: urlModel, field }
		});
}

export const urlmodelIdFieldPATCH: RequestHandler<ParamsUrlmodelIdField> = async ({
	fetch,
	params,
	request
}) => {
	const model = getModelInfo(params.model);
	const endpoint = `${BASE_API_URL}/${model.endpointUrl ?? params.model}/${params.id}/`;

	const body = await request.json();

	const payload = {
		[params.field]: body[params.field]
	};

	const res = await fetch(endpoint, { method: 'PATCH', body: JSON.stringify(payload) });
	if (!res.ok) {
		error(res.status as NumericRange<400, 599>, await res.json());
	}
	const data = await res.json();

	return new Response(JSON.stringify(data), {
		status: res.status,
		headers: {
			'Content-Type': 'application/json'
		}
	});
};

/** Generic `PATCH` request handler for any API routes matching `(app)/(internal)/[model=urlmodel]/[id=uuid]/[field=fields]/+server.ts`.
 *
 * Example for `(app)/(internal)/asset-assessments/[id=uuid]/dependencies/+server.ts`:
 *
 * ```ts
 * export const PATCH = genericUrlmodelIdFieldPATCH("asset-assessments", "dependencies");
 * ```
 */
export function genericUrlmodelIdFieldPATCH(
	urlModel: urlModel,
	field: string
): typeof urlmodelIdFieldPATCH {
	return async (event) =>
		urlmodelIdPATCH({
			...event,
			params: { ...event.params, model: urlModel, field }
		});
}
