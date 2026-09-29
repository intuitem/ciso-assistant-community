import type { BatchActionConfig } from '$lib/utils/table';

/** Overlays the community stub: this edition allows nested domains, so a domain
 * can be reparented. Each selected domain is reparented on its own, so selecting
 * a domain and its descendants moves them all to the target rather than keeping
 * the descendants under their former parent. */
export const folderBatchActions: BatchActionConfig[] = [
	{
		type: 'change_field',
		label: 'changeParentDomain',
		icon: 'fa-solid fa-folder-tree',
		field: 'parent_folder',
		optionsEndpoint: 'folders?content_type=DO&content_type=GL',
		excludeSelectedSubtree: true
	}
];
