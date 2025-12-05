import type { Page as _Page } from '@playwright/test';
import type { Expect } from '@playwright/test';
import { Sidebar } from '../derived/sidebar';
import { Element } from './element';

/** This is a fundamental class, it must be inherited by any base/derived class that represents a specific web page. */
export class Page {
	protected _self: _Page;
	protected _endpoint: string;

	/**
	 * @param page - The page object given by the playwright page fixture.
	 * @param endpoint - The endpoint of this page (e.g. "/login").
	 */
	constructor(page: _Page, endpoint: string) {
		this._self = page;
		// Can we make it so the endpoint should id a Page static variable !
		this._endpoint = endpoint;
	}

	/** Returns the underlying playwright Page of this object. */
	getSelf(): _Page {
		return this._self;
	}

	/** Check if the browser's URL match the expected endpoint. */
	async checkSelf(expect: Expect) {
		await expect(this._self).toHaveURL(this._endpoint);
	}

	/** Goto the page (by using the endpoint given to its constructor). */
	async gotoSelf() {
		await this._self.goto(this._endpoint);
	}

	/**
	 * Retrieves a sub-element instance of the specified element class, applying locator filters and optionally passing it a context.
	 *
	 * @template T - The type of the Element class to instantiate.
	 * @param elementClass - The constructor of the Element class, which must have a static `DATA_TESTID` property.
	 * @param filters - Optional locator filters used to refine the element selection. Defaults to an empty object.
	 * @param context - Optional context to be passed to the element instance. Defaults to an empty object.
	 * @returns A new instance of the specified element class (`InstanceType<T>`).
	 *
	 * @throws If the static `DATA_TESTID` property is missing on the provided element class.
	 *
	 * @remarks
	 * This method extracts a data test identifier from either the provided filters or the static `DATA_TESTID` property
	 * of the element class. It uses this identifier to obtain a locator, then applies additional filters (like `nth`, `first`,
	 * or `last`) to narrow down the element selection. Finally, it instantiates the element class with the resolved locator, the super-element (`this`) and the context.
	 */
	protected _getSubElement<T extends Element.Class<any>>(
		elementClass: T,
		filters: Element.LocatorFilters = {},
		context: Element.Context = {}
	): InstanceType<T> {
		// This is just a temporary proxy element which will not be stored in the this._chain of the sub-elements of this page.
		const rootElement = new Element(this._self.locator(':root'), this);
		// @ts-ignore: This will be the only time _getSubElement is accessed outside of an Element class.
		return rootElement._getSubElement(elementClass, filters, context, this);
	}

	/**
	 * Creates and returns an instance of the specified `pageClass`.
	 *
	 * @param pageClass - The class constructor to instantiate.
	 * @param endpoint - An optional endpoint string to pass to the class constructor.
	 *
	 * @returns An instance of the `pageClass`, initialized with the current context and optional endpoint.
	 */
	protected _getGoto<T extends Page.Class<any>>(pageClass: T, endpoint?: string): InstanceType<T> {
		return new pageClass(this._self, endpoint);
	}

	/**
	 * Close a modal by clicking outside of it.
	 * This method specifically clicks at coordinates (1, 1) which is supposed to outside of the modal.
	 * This way of closing modal may not work for all modals.
	 */
	async doCloseModal() {
		await this._self.mouse.click(1, 1);
	}
}
export namespace Page {
	export type Class<T> = new (page: _Page, endpoint: string | undefined) => T;
}

interface HaveSidebarI {
	/** [data-testid="sidebar"] Get the `<Sidebar/>` of the page. */
	getSidebar(): Sidebar;
}

/** Represents the presence of a `<Sidebar/>` component in the page. */
export function HaveSidebar<T extends new (...args: any[]) => Page>(
	PageClass: T
): new (...args: ConstructorParameters<T>) => InstanceType<T> & HaveSidebarI {
	return class extends PageClass implements HaveSidebarI {
		getSidebar() {
			return this._getSubElement(Sidebar);
		}
	} as any;
}
