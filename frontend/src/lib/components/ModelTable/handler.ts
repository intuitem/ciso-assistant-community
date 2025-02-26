import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import { tableSourceMapper } from '@skeletonlabs/skeleton';
import type { State } from '@vincjo/datatables/remote';
import type { TableSource } from './types';

export const loadTableData = async (state: State, URLModel: urlModel, endpoint: string) => {
	const response = await fetch(`${endpoint}?${getParams(state)}`).then((res) => res.json());
	state.setTotalRows(response.count);

	const bodyData = tableSourceMapper(response.results, listViewFields[URLModel as urlModel].body);

	const headData: Record<string, string> = listViewFields[URLModel as urlModel].body.reduce(
		(obj, key, index) => {
			obj[key] = listViewFields[URLModel as urlModel].head[index];
			return obj;
		},
		{}
	);

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
