import { BASE_API_URL } from '$lib/utils/constants';
import { listViewFields } from '$lib/utils/table';
import type { urlModel } from '$lib/utils/types';
import { tableSourceMapper } from '@skeletonlabs/skeleton';
import type { State } from '@vincjo/datatables/remote';
import type { TableSource } from './types';

export const loadTableData = async (state: State, URLModel: urlModel, endpoint: string) => {
	const response = await fetch(`${endpoint}/?${getParams(state)}`).then((res) => res.json());
	state.setTotalRows(response.count);

	const bodyData = tableSourceMapper(response, listViewFields[URLModel as urlModel].body);

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
		return { ...item, meta: table.meta ? { ...table.meta[index] } : undefined };
	});
};

const getParams = ({ offset, rowsPerPage, search, sort, filters }: State) => {
	let params = `offset=${offset}&limit=${rowsPerPage}`;
	//
	// if (search) {
	// 	params += `&q=${search}`;
	// }
	if (sort) {
		params += `&ordering=${sort.direction === 'desc' ? '-' : ''}${sort.orderBy}`;
	}
	// if (filters) {
	// 	params += filters.map(({ filterBy, value }) => `&${filterBy}=${value}`).join('');
	// }
	return params;
};
