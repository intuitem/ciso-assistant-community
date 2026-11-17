import type { Page } from '@playwright/test';
import type { Annotation } from './manifest.js';

const STYLE_ID = 'docs-shots-annotations';

/**
 * Overlay callout boxes on the page before capture.
 *
 * Boxes are positioned in *document* coordinates rather than viewport ones, so
 * they stay attached to their target in `fullPage` captures and in element
 * clips, both of which scroll or offset the frame away from the viewport.
 */
export async function annotate(page: Page, annotations: Annotation[]): Promise<void> {
	const boxes: { x: number; y: number; width: number; height: number; label?: string }[] = [];

	for (const { at, label } of annotations) {
		await at.scrollIntoViewIfNeeded();
		const box = await at.boundingBox();
		if (!box) {
			throw new Error(`annotation target is not visible: ${at}`);
		}
		const offset = await page.evaluate(() => ({ x: window.scrollX, y: window.scrollY }));
		boxes.push({ ...box, x: box.x + offset.x, y: box.y + offset.y, label });
	}

	await page.evaluate(
		({ boxes, styleId }) => {
			document.getElementById(styleId)?.remove();
			const style = document.createElement('style');
			style.id = styleId;
			style.textContent = `
				.docs-shot-callout {
					position: absolute;
					border: 3px solid #e8005f;
					border-radius: 6px;
					box-shadow: 0 0 0 3px rgba(232, 0, 95, 0.18);
					pointer-events: none;
					z-index: 2147483000;
				}
				.docs-shot-badge {
					position: absolute;
					transform: translate(-55%, -55%);
					min-width: 26px;
					height: 26px;
					padding: 0 7px;
					border-radius: 999px;
					background: #e8005f;
					color: #fff;
					font: 700 15px/26px ui-sans-serif, system-ui, sans-serif;
					text-align: center;
					box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
					pointer-events: none;
					z-index: 2147483001;
				}
			`;
			document.head.append(style);

			for (const box of boxes) {
				const outline = document.createElement('div');
				outline.className = 'docs-shot-callout';
				outline.style.left = `${box.x - 3}px`;
				outline.style.top = `${box.y - 3}px`;
				outline.style.width = `${box.width + 6}px`;
				outline.style.height = `${box.height + 6}px`;
				document.body.append(outline);

				if (box.label !== undefined) {
					const badge = document.createElement('div');
					badge.className = 'docs-shot-badge';
					badge.style.left = `${box.x}px`;
					badge.style.top = `${box.y}px`;
					badge.textContent = box.label;
					document.body.append(badge);
				}
			}
		},
		{ boxes, styleId: STYLE_ID }
	);
}
