export const meta = {
	type: 'problem',
	docs: {
		description: 'Detect potential open redirect vulnerabilities in SvelteKit redirects',
		category: 'Security',
		recommended: true
	},
	fixable: 'code',
	schema: []
};
export function create(context) {
	return {
		CallExpression(node) {
			if (node.callee.name === 'redirect' && node.arguments.length === 2) {
				const statusArg = node.arguments[0];
				const locationArg = node.arguments[1];

				// Check if status is within the valid range (300-308)
				if (statusArg.type === 'Literal' && (statusArg.value < 300 || statusArg.value > 308)) {
					context.report({
						node: statusArg,
						message: 'Invalid status code for redirect. Must be between 300 and 308.'
					});
				}

				// Check if location is potentially unsafe
				if (
					locationArg.type !== 'Literal' &&
					locationArg.type !== 'TemplateLiteral' &&
					!(
						locationArg.type === 'CallExpression' && locationArg.callee.name === 'getSecureRedirect'
					)
				) {
					context.report({
						node: locationArg,
						message:
							'Potential open redirect vulnerability. Use getSecureRedirect() for dynamic URLs.',
						fix: function (fixer) {
							return fixer.replaceText(
								locationArg,
								`getSecureRedirect(${context.getSourceCode().getText(locationArg)})`
							);
						}
					});
				} else if (locationArg.type === 'TemplateLiteral' && locationArg.expressions.length > 0) {
					context.report({
						node: locationArg,
						message:
							'Potential open redirect vulnerability in template literal. Use getSecureRedirect().',
						fix: function (fixer) {
							return fixer.replaceText(
								locationArg,
								`getSecureRedirect(${context.getSourceCode().getText(locationArg)})`
							);
						}
					});
				}
			}
		}
	};
}
