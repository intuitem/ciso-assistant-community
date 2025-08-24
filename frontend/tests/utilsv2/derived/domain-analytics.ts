import { Element } from '../core/element';
import { DomainAnalyticsTreeViewNode } from './domain-analytics-treeview';

/** Represents the domain-analytics `<main>` HTML element wrapping its root TreeView component. */
export class DomainAnalytics extends Element {
	static DATA_TESTID = 'domain-analytics-elem';

	constructor(...args: Element.Args) {
		super(...args);
	}

	/** Returns domain-analytics `<TreeView/>` node which represents the Global domain. */
	getGlobalFolderTreeViewNode(): DomainAnalyticsTreeViewNode {
		return this._getSubElement(DomainAnalyticsTreeViewNode, { first: true });
	}
}
