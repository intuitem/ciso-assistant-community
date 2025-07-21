import { Element } from '../core/element';
import type { Locator, Expect } from '@playwright/test';
import * as m from '$paraglide/messages';

// This class is dead code, but let's keep it for now.

/** Represents the `<footer>` of the `<ModelTable/>`. */
export class ModelTableFooter extends Element {
	static DATA_TESTID = 'model-table-footer-elem';
	_rowCounter: Locator;

	constructor(...args: Element.Args) {
		super(...args);
		this._rowCounter = this.getSelf().getByTestId('row-count-elem');
	}
}
