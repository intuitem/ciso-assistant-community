import type { BatchActionConfig } from '$lib/utils/table';

/** Batch actions on domains that only an edition allowing nested domains offers.
 * Community domains all sit directly under the root, so reparenting has no target
 * to offer and the backend rejects it (`subDomainsRequirePro`); an edition that
 * allows nesting overlays this file. Kept as a data module so the batch-action
 * registry itself is never duplicated. */
export const folderBatchActions: BatchActionConfig[] = [];
