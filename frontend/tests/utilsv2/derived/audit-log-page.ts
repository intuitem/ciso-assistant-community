import type { Page as _Page } from '@playwright/test';
import { ListViewPage } from '../base/list-view-page';

/** Represents the `/audit-log` page. */
export class AuditLogPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/audit-log');
	}
}
