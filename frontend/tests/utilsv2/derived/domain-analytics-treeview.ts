import { Element } from '../core/element';
import type { Locator, Expect } from '@playwright/test';

/** Represents the domain-analytics `<TreeView/>` component. */
export class DomainAnalyticsTreeViewNode extends Element {
	static DATA_TESTID = 'domain-analytics-treeview';
	private _expandArrow: Locator;
	private _labelText: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._expandArrow = this._self.getByTestId('treeview-expand-arrow-elem').first();
		this._labelText = this._self.getByTestId('treeview-label-text-elem').first();
	}

	/** Returns true if the node is expandable and expanded, otherwise return false. */
	async getIsExpanded(): Promise<{ isExpandable: boolean; isExpanded: boolean }> {
		const isExpandable = await this._expandArrow.isVisible();
		if (!isExpandable) return { isExpandable, isExpanded: false };

		const arrowClasses = await this._expandArrow.getAttribute('class');
		if (!arrowClasses) return { isExpandable, isExpanded: false };

		const isExpanded = arrowClasses?.indexOf('arrowDown') >= 0;
		return { isExpandable, isExpanded };
	}

	/** Expands the tree view item if it's expandable, if it's already expanded does nothing. */
	async doExpand(expect: Expect) {
		const { isExpandable, isExpanded } = await this.getIsExpanded();
		if (!isExpandable || isExpanded) return;

		this._expandArrow.click();
		await expect(
			this._self.getByTestId(DomainAnalyticsTreeViewNode.DATA_TESTID).first()
		).toBeVisible();
	}

	/** Expands the tree view item if needed and returns the list of its visible tree view item descendants. */
	async getVisibleDescendants(expect: Expect): Promise<DomainAnalyticsTreeViewNode[]> {
		const { isExpandable } = await this.getIsExpanded();
		if (!isExpandable) return [];

		await this.doExpand(expect);
		const descendantLocators = await this._self
			.getByTestId(DomainAnalyticsTreeViewNode.DATA_TESTID)
			.filter({ visible: true })
			.all();
		return descendantLocators.map((locator) =>
			this._getSubElementFromLocator(locator, DomainAnalyticsTreeViewNode)
		);
	}

	/** Returns the clean tree view node text (without the UTF-8 arrow and without whitespaces). */
	async getLabelText(): Promise<string> {
		return this._labelText.innerText();
	}
}
