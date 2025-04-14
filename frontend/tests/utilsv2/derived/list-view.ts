import { ListViewPage } from '../base/list-view-page';
import { FolderCreateModal } from './create-modal';
import type { Page as _Page } from '@playwright/test';
import type { Element } from '../core/element';

export class FolderListViewPage extends ListViewPage {
	static CONTEXT: Element.Context = {
		URLModel: '/folders'
	};

	constructor(page: _Page) {
		super(page, '/folders');
	}

	async getOpenCreateModal(): Promise<FolderCreateModal> {
		return super._getOpenCreateModal(FolderCreateModal);
	}
}
