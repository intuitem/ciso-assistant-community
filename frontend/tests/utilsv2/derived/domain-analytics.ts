import { Element } from '../core/element';
import { DomainAnalyticsTreeViewNode } from './domain-analytics-treeview';

export class DomainAnalaytics extends Element {
	static DATA_TESTID = 'domain-analytics';

	constructor(...args: Element.Args) {
		super(...args);
	}

	getGlobalFolderTreeViewNode(): DomainAnalyticsTreeViewNode {
		return this._getSubElement(DomainAnalyticsTreeViewNode, { first: true });
	}
}
