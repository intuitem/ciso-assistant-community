import { fetchAllByIds } from '$lib/utils/pagination';

export const idOf = (ref: any): string => (typeof ref === 'object' && ref !== null ? ref.id : ref);

export function createLinkWriter(notifyError: (message: string) => void) {
	const queues = new Map<string, Promise<boolean>>();

	async function patchParentAssets(childId: string, parentIds: string[]): Promise<boolean> {
		try {
			const res = await fetch(`/assets/${childId}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ parent_assets: parentIds })
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				const msg =
					(err && (err.parent_assets || err.detail || err.non_field_errors)) ?? 'Update failed';
				notifyError(typeof msg === 'string' ? msg : JSON.stringify(msg));
				return false;
			}
			return true;
		} catch {
			notifyError('Network error updating asset relationship');
			return false;
		}
	}

	function updateParents(
		childId: string,
		change: (parents: string[]) => string[]
	): Promise<boolean> {
		const run = async () => {
			let current: string[];
			try {
				const [row] = await fetchAllByIds<{ parent_assets?: unknown[] }>(fetch, '/assets', [
					childId
				]);
				if (!Array.isArray(row?.parent_assets)) throw new Error('parents unavailable');
				current = row.parent_assets.map(idOf);
			} catch {
				notifyError('Network error updating asset relationship');
				return false;
			}
			return patchParentAssets(childId, change(current));
		};
		const queued = (queues.get(childId) ?? Promise.resolve(true)).then(run, run);
		queues.set(childId, queued);
		void queued.finally(() => {
			if (queues.get(childId) === queued) queues.delete(childId);
		});
		return queued;
	}

	return { updateParents };
}
