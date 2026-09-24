import type { SelectField, SelectFieldData } from '$lib/utils/crud';

export function formatSelectFieldData(
	responseData: Record<string, string>,
	selectField: SelectField
): SelectFieldData[] {
	const isNumber = selectField.valueType === 'number';
	const isOptionList = Array.isArray(responseData);

	let fieldOptions = [];

	if (isOptionList) {
		fieldOptions = responseData.map((option) => ({
			label: option.label,
			value: isNumber ? parseInt(option.value) : option.value
		}));
	} else {
		fieldOptions = Object.entries(responseData).map(([key, value]) => ({
			label: value,
			value: isNumber ? parseInt(key) : key
		}));
	}

	if (isNumber) {
		fieldOptions.sort((a, b) => a.value - b.value);
	}
	return fieldOptions;
}
