import { test as testV2, expect as expectV2 } from '../utilsv2/core/base';

import { LoginPage } from '../utilsv2/derived/login-page';
import { FolderListViewPage } from '../utilsv2/derived/list-view';
import { DomainAnalyticsPage } from '../utilsv2/derived/domain-analytics-page';
import { DomainAnalyticsTreeViewNode } from '../utilsv2/derived/domain-analytics-treeview';

const TEST_DATA = [
	{ name: 'Domain 1' },
	{ name: 'Domain 2', parentDomain: 'Domain 1' },
	{ name: 'Domain 3', parentDomain: 'Domain 1' },
	{ name: 'Domain 4', parentDomain: 'Domain 3' },
	{ name: 'Domain 5', parentDomain: 'Domain 3' }
];

type DomainTree = { [key: string]: DomainTree | null };

const DOMAIN_TREE: DomainTree = {
	'Domain 1': {
		'Domain 2': null,
		'Domain 3': {
			'Domain 4': null,
			'Domain 5': null
		}
	}
};

testV2('domain-analytics test', async ({ page }) => {
	const loginPage = new LoginPage(page);
	await loginPage.gotoSelf();
	const analyticsPage = await loginPage.doLoginAdminP();
	await analyticsPage.doCloseModal();

	const listView = new FolderListViewPage(page);
	listView.gotoSelf();
	listView.checkSelf(expectV2);
	for (const folder of TEST_DATA) {
		const createModal = await listView.getOpenCreateModal();
		const createForm = await createModal.getForm();
		await createForm.doFillForm(folder);
		await createForm.doSubmit();
	}

	const domainAnalyticsPage = new DomainAnalyticsPage(page);
	await domainAnalyticsPage.gotoSelf();
	await domainAnalyticsPage.checkSelf(expectV2);
	const domainAnalytics = domainAnalyticsPage.getDomainAnalytics();
	let globalDomainNode = domainAnalytics.getGlobalFolderTreeViewNode();
	const globalDomainName = await globalDomainNode.getLabelText();
	await expectV2(globalDomainName).toBe('Global');

	/** Checks if the domain-analytics `<TreeView/>` nodes in the DOM match the structure of of the root/some part of the `DOMAIN_TREE`. */
	async function checkDomainTree(nodes: DomainAnalyticsTreeViewNode[], domainTree: DomainTree) {
		await expectV2(nodes.length).toBe(Object.keys(domainTree).length);

		for (const [i, [domainName, subdomainTree]] of Object.entries(domainTree).map((data, i) => [
			i,
			data
		])) {
			const currentNode = nodes[i];
			const nodeLabelText = await currentNode.getLabelText();
			await expectV2(nodeLabelText).toBe(domainName);
			const currentDescendants = await currentNode.getVisibleDescendants(expectV2);
			if (subdomainTree === null) {
				expectV2(currentDescendants.length).toBe(0);
				continue;
			}
			await checkDomainTree(currentDescendants, subdomainTree);
		}
	}

	const nodes = await globalDomainNode.getVisibleDescendants(expectV2);
	await checkDomainTree(nodes, DOMAIN_TREE);
});
