import { aggregateReports, cleanReports } from './utils/a11y-report.js';

// Returns a teardown (Playwright convention) that builds the combined report.
export default function globalSetup() {
	cleanReports();
	return () => aggregateReports();
}
