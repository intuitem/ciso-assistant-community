export async function renderDocx(blob: Blob): Promise<{ body: string; css: string }> {
	const { renderAsync } = await import('docx-preview');
	const doc = document.implementation.createHTMLDocument('');
	const styleContainer = doc.createElement('div');
	const bodyContainer = doc.createElement('div');
	doc.body.append(styleContainer, bodyContainer);

	await renderAsync(blob, bodyContainer, styleContainer, {
		inWrapper: true,
		ignoreFonts: true,
		breakPages: false,
		useBase64URL: true
	});
	bodyContainer.querySelectorAll('a[href]').forEach((anchor) => anchor.removeAttribute('href'));

	return { body: styleContainer.innerHTML + bodyContainer.innerHTML, css: 'body{margin:0}' };
}
