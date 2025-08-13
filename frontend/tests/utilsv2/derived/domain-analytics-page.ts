import { Page } from '../core/page';
import { DomainAnalytics } from './domain-analytics';
import type { Page as _Page } from '@playwright/test';

/** Represents the `/domain-analytics` page. (enterprise version) */
export class DomainAnalyticsPage extends Page {
	constructor(page: _Page) {
		super(page, '/domain-analytics');
	}

	getDomainAnalytics(): DomainAnalytics {
		return this._getSubElement(DomainAnalytics);
	}
}
