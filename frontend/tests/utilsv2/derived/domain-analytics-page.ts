import { Page } from '../../utilsv2/core/page';
import { DomainAnalaytics } from '../../utilsv2/derived/domain-analytics';
import type { Page as _Page } from '@playwright/test';

export class DomainAnalyticsPage extends Page {
	constructor(page: _Page) {
		super(page, '/domain-analytics');
	}

	getDomainAnalytics(): DomainAnalaytics {
		return this._getSubElement(DomainAnalaytics);
	}
}
