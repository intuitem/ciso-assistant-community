import { Element } from '../core/element';

export class ModelTable extends Element {
	static DATA_TESTID = 'model-table';
	_columnNames: string[] | null;

	constructor(...args: Element.Args) {
		super(...args);
		this._columnNames = null;
	}

	getRow() {}
}
