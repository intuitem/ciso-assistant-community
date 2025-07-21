import { Element } from '../core/element';

/** Represents the filter button (and filter box) of the `<ModelTable/>`. */
export class ModelTableFilter extends Element {
	static DATA_TESTID = 'model-table-filter-elem';

	constructor(...args: Element.Args) {
		super(...args);
	}

	/** Closes the filter box by clicking outside of it. */
	async doClose(): Promise<void> {
		await this._getPage().doCloseModal();
	}

	/**
	 * Applies a filter to a given field using one or more specified values.
	 * Note that this function only work for SelectFilter filters.
	 *
	 * @param field - The name of the field which will be filtered out.
	 * @param values - One or multiple values that will be selected in the filter Multi-Select component of the specified field.
	 */
	async doApplyFilter(field: string, values: string | string[]) {
		if (!Array.isArray(values)) {
			values = [values];
		}

		const filterDataTestId = `filter-${field.replace('_', '-')}`;
		const filter = this._self.getByTestId(filterDataTestId);
		await filter.click();

		const mutliSelect = filter.getByRole('searchbox');
		const filterChoices = await filter.locator('ul').last().locator('li').all();
		await mutliSelect.click();

		const filterChoicesMap = Object.fromEntries(
			await Promise.all(
				filterChoices.map(async (choiceElem) => {
					const innerText = await choiceElem.innerText();
					return [innerText, choiceElem];
				})
			)
		);

		for (const value of values) {
			const choice = filterChoicesMap[value];
			if (!choice) {
				console.error(
					`[ERROR:doApplyFilter] the '${value}' hasn't been found in the '${field}' filter.`
				);
				continue;
			}
			await choice.click();
		}

		await this.doClose();
	}
}
