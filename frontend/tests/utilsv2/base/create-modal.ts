import { notImplemented } from '../core/base';
import { ModelForm } from './model-form';
import { Element } from '../core/element';
import type { Page as _Page } from '@playwright/test';

export class CreateModal extends Element {
	static DATA_TESTID: string = 'modal-component';

	getForm(): ModelForm {
		notImplemented();
	}
}
