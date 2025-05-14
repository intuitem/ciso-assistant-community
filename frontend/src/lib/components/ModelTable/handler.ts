import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import type { State } from '@vincjo/datatables/remote';
import type { TableSource } from './types';

export interface LoadTableDataParams {
	state: State;
	URLModel: urlModel;
	endpoint: string;
	fields?: string[];
}

export const loadTableData = async ({ state, URLModel, endpoint, fields }: LoadTableDataParams) => {
	const url = new URL(endpoint, window.location.origin);
	const params = new URLSearchParams(url.search);
	const newParams = getParams(state);

	newParams.forEach((value, key) => params.append(key, value));
	url.search = params.toString();

	const response = await fetch(url.toString()).then((res) => res.json());
	state.setTotalRows(response.count);

	const fieldsToUse =
		fields.length > 0
			? { ...listViewFields[URLModel as urlModel], head: fields, body: fields }
			: listViewFields[URLModel as urlModel];
	const bodyData = tableSourceMapper(response.results, fieldsToUse.body);

	const headData: Record<string, string> = fieldsToUse.body.reduce((obj, key, index) => {
		obj[key] = fieldsToUse.head[index];
		return obj;
	}, {});

	const table: TableSource = {
		head: headData,
		body: bodyData,
		meta: response // metaData
	};

	return table.body.map((item: Record<string, any>, index: number) => {
		return { ...item, meta: table?.meta?.results ? { ...table.meta.results[index] } : undefined };
	});
};

const getParams = ({ offset, rowsPerPage, search, sort, filters }: State) => {
	const params = new URLSearchParams();
	params.set('offset', offset.toString() ?? '0');
	params.set('limit', rowsPerPage.toString() ?? '10');
	if (search) {
		params.set('search', search);
	}
	if (sort) {
		params.set('ordering', `${sort.direction === 'desc' ? '-' : ''}${sort.orderBy}`);
	}
	if (filters) {
		for (const filter of filters) {
			const filterKey = filter.filterBy.toString();
			if (Array.isArray(filter.value)) {
				for (const val of filter.value) {
					params.append(filterKey, val.toString());
				}
			} else if (filter.value) {
				params.append(filterKey, filter.value.toString());
			}
		}
	}
	return params;
};
