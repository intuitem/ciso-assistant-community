import { parseXlsx } from './parseXlsx';
import type { WorkerRequest } from './types';

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
	try {
		self.postMessage({ ok: true, model: await parseXlsx(event.data.buffer) });
	} catch {
		self.postMessage({ ok: false });
	}
};
