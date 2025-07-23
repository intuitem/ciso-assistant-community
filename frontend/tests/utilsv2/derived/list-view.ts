import { ListViewPage } from '../base/list-view-page';
import {
	FolderCreateModal,
	PerimeterCreateModal,
	AssetCreateModal,
	AppliedControlCreateModal,
	ExceptionCreateModal,
	ComplianceAssessmentCreateModal,
	EvidenceCreateModal,
	RiskAssessmentCreateModal,
	ThreatCreateModal,
	RiskScenarioCreateModal,
	RiskAcceptanceCreateModal,
	UserCreateModal
} from './create-modal';
import type { Page as _Page, Expect, Locator } from '@playwright/test';
import type { Element } from '../core/element';
import { safeTranslate } from '$lib/utils/i18n';

export class FolderListViewPage extends ListViewPage {
	static CONTEXT: Element.Context = {
		URLModel: 'folders'
	};

	constructor(page: _Page) {
		super(page, '/folders');
	}

	/** Represents the presence of a "Create Object" button which opens a <CreateModal/> component when clicked. */
	async getOpenCreateModal(): Promise<FolderCreateModal> {
		return super._getOpenCreateModal(FolderCreateModal);
	}
}

export class PerimeterListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/perimeters');
	}

	async getOpenCreateModal(): Promise<PerimeterCreateModal> {
		return super._getOpenCreateModal(PerimeterCreateModal);
	}
}

export class AssetListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/assets');
	}

	async getOpenCreateModal(): Promise<AssetCreateModal> {
		return super._getOpenCreateModal(AssetCreateModal);
	}
}

export class AppliedControlListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/applied-controls');
	}

	async getOpenCreateModal(): Promise<AppliedControlCreateModal> {
		return super._getOpenCreateModal(AppliedControlCreateModal);
	}
}

export class ExceptionListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/security-exceptions');
	}

	async getOpenCreateModal(): Promise<ExceptionCreateModal> {
		return super._getOpenCreateModal(ExceptionCreateModal);
	}
}

export class ComplianceAssessmentListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/compliance-assessments');
	}

	async getOpenCreateModal(): Promise<ComplianceAssessmentCreateModal> {
		return super._getOpenCreateModal(ComplianceAssessmentCreateModal);
	}
}

export class EvidenceListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/evidences');
	}

	async getOpenCreateModal(): Promise<EvidenceCreateModal> {
		return super._getOpenCreateModal(EvidenceCreateModal);
	}
}

export class RiskAssessmentListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/risk-assessments');
	}

	async getOpenCreateModal(): Promise<RiskAssessmentCreateModal> {
		return super._getOpenCreateModal(RiskAssessmentCreateModal);
	}
}

export class ThreatListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/threats');
	}

	async getOpenCreateModal(): Promise<ThreatCreateModal> {
		return super._getOpenCreateModal(ThreatCreateModal);
	}
}

export class RiskScenarioListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/risk-scenarios');
	}

	async getOpenCreateModal(): Promise<RiskScenarioCreateModal> {
		return super._getOpenCreateModal(RiskScenarioCreateModal);
	}
}

export class RiskAcceptanceListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/risk-acceptances');
	}

	async getOpenCreateModal(): Promise<RiskAcceptanceCreateModal> {
		return super._getOpenCreateModal(RiskAcceptanceCreateModal);
	}
}

export class UserListViewPage extends ListViewPage {
	constructor(page: _Page) {
		super(page, '/users');
	}

	async getOpenCreateModal(): Promise<UserCreateModal> {
		return super._getOpenCreateModal(UserCreateModal);
	}
}

export class LibraryListViewPage extends ListViewPage {
	protected _tabs: Locator;
	protected _libraryStoreTab: Locator;
	protected _loadedLibrariesTab: Locator;

	constructor(page: _Page) {
		super(page, '/libraries');
		this._tabs = page.getByTestId('tabs-control');
		this._libraryStoreTab = this._tabs.first();
		this._loadedLibrariesTab = this._tabs.last();
	}

	/** Clicks on the the "Library store" <Tab/> component. */
	async doClickLibraryStoreTab() {
		await this._libraryStoreTab.click();
	}

	/** Clicks on the the "Loaded libraries{...}" <Tab/> component. */
	async doClickLoadedLibrariesTab() {
		await this._loadedLibrariesTab.click();
	}

	/** Checks that the current number of loaded libraries is of `count` by reading the innerText of the "Loaded libraries{...}" <Tab/> component. */
	async checkLoadedLibraryCount(expect: Expect, count: number) {
		if (count < 1) {
			return await expect(this._tabs).toHaveCount(0);
		}
		await expect(this._tabs).toHaveCount(2);
		await expect(this._loadedLibrariesTab).toHaveText(
			`${safeTranslate('loadedLibraries')} ${count}`
		);
	}

	/** Returns the number of currently loaded libraries. */
	async getLoadedLibraryCount(): Promise<number> {
		const text = await this._loadedLibrariesTab.innerText();
		const libraryCount = Number(text.match(/[0-9]+$/));
		return libraryCount;
	}
}
