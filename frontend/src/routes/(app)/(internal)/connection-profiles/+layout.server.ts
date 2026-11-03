import { listViewFields } from '$lib/utils/table';
import { type TableSource } from '$lib/components/ModelTable/types';
import { urlParamModelVerboseName, urlParamModelDescriptionKey } from '$lib/utils/crud';
import type { LayoutServerLoad } from './$types';

const URLModel = 'connection-profiles';

// reachable with MCP off, like Connected apps: an admin may set profiles up first
export const load: LayoutServerLoad = async () => {
	const base = listViewFields[URLModel];
	const headData: Record<string, string> = base.body.reduce((obj, key, index) => {
		obj[key] = base.head[index];
		return obj;
	}, {});

	const table: TableSource = {
		head: headData,
		body: [],
		meta: []
	};

	return {
		table,
		modelVerboseName: urlParamModelVerboseName(URLModel),
		modelDescriptionKey: urlParamModelDescriptionKey(URLModel)
	};
};
