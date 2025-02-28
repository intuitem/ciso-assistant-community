import { Page, HaveSidebar } from '../core/page';
import type { Page as _Page } from '@playwright/test';

/** Represents the `/analytics` page. */
export class AnalyticsPage extends HaveSidebar(Page) {
	constructor(page: _Page) {
		super(page, '/analytics');
	}
}
