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

const SAFE_HELPER = 'getSecureRedirect';

// Mirrors getSecureRedirect()'s own SECURE_REDIRECT_URL_REGEX: a leading slash
// followed by a word character. `/${x}` and `//${x}` are excluded on purpose --
// they can resolve to a protocol-relative URL and leave the origin.
const SAME_ORIGIN_PREFIX = /^\/\w/;

function isSafeHelperCall(node) {
	return (
		node &&
		node.type === 'CallExpression' &&
		(node.callee.name === SAFE_HELPER ||
			(node.callee.type === 'MemberExpression' && node.callee.property.name === SAFE_HELPER))
	);
}

/** Resolve an identifier to the initializer of its single, never-reassigned definition. */
function resolveIdentifier(node, scope) {
	let current = scope;
	while (current) {
		const variable = current.variables.find((v) => v.name === node.name);
		if (variable) {
			const writes = variable.references.filter((r) => r.isWrite());
			if (writes.length !== 1) return null;
			const def = variable.defs[0];
			return def && def.node && def.node.type === 'VariableDeclarator' ? def.node.init : null;
		}
		current = current.upper;
	}
	return null;
}

function isSafeTarget(node, scope, depth = 0) {
	if (!node || depth > 5) return false;

	switch (node.type) {
		case 'Literal':
			return true;
		case 'TemplateLiteral':
			// No interpolation, or a literal prefix that pins the result to this origin.
			return (
				node.expressions.length === 0 || SAME_ORIGIN_PREFIX.test(node.quasis[0].value.cooked ?? '')
			);
		case 'CallExpression':
			return isSafeHelperCall(node);
		case 'LogicalExpression':
			return (
				isSafeTarget(node.left, scope, depth + 1) && isSafeTarget(node.right, scope, depth + 1)
			);
		case 'ConditionalExpression':
			return (
				isSafeTarget(node.consequent, scope, depth + 1) &&
				isSafeTarget(node.alternate, scope, depth + 1)
			);
		case 'Identifier':
			return isSafeTarget(resolveIdentifier(node, scope), scope, depth + 1);
		default:
			return false;
	}
}

export function create(context) {
	return {
		CallExpression(node) {
			if (node.callee.name !== 'redirect' || node.arguments.length !== 2) return;

			const statusArg = node.arguments[0];
			const locationArg = node.arguments[1];

			if (statusArg.type === 'Literal' && (statusArg.value < 300 || statusArg.value > 308)) {
				context.report({
					node: statusArg,
					message: 'Invalid status code for redirect. Must be between 300 and 308.'
				});
			}

			const scope = context.sourceCode.getScope(node);
			if (isSafeTarget(locationArg, scope)) return;

			const message =
				locationArg.type === 'TemplateLiteral'
					? 'Potential open redirect vulnerability in template literal. Use getSecureRedirect().'
					: 'Potential open redirect vulnerability. Use getSecureRedirect() for dynamic URLs.';

			context.report({
				node: locationArg,
				message,
				fix: (fixer) =>
					fixer.replaceText(
						locationArg,
						`${SAFE_HELPER}(${context.sourceCode.getText(locationArg)})`
					)
			});
		}
	};
}

export default {
	meta,
	create
};
