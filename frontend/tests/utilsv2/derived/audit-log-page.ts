import { Page, HaveSidebar } from '../core/page';
import type { Page as _Page } from '@playwright/test';

/** Represents the `/audit-log` page. */
export class AuditLogPage extends HaveSidebar(Page) {
	constructor(page: _Page) {
		super(page, '/audit-log');
	}
}
