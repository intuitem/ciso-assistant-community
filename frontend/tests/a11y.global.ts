import { aggregateReports, cleanReports } from './utils/a11y-report.js';

// Playwright global setup: clean stale per-page reports, then return a teardown
// that folds the fresh per-page files into the combined report.
export default function globalSetup() {
	cleanReports();
	return () => aggregateReports();
}
