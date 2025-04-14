import ts from 'typescript';
import path from 'path';
import { readFileSync } from 'fs';
import type { TestInfo, TestInfoError, TestType, Page as _Page } from '@playwright/test';
import type { AllFixtures } from './fixtures';
import { test, expect } from './base';

// These imports are dependencies required to run the _start entry point with eval(finalCode) .
import { expect as baseExpect } from '@playwright/test';
import { test as base } from '@playwright/test';
var __EVAL_DEPENDENCIES__ = [baseExpect, base];
// The __EVAL_DEPENDENCIES__ variable is unused, its goal is to "register" the imported variables by storing them in a variable.
// By being stored in a list these variables get loaded into the global scope (an import doesn't load the imported variable into the global scope if it's unused).
// Doing so gives the ability to the eval function to access them.

interface FileInfo {
	dependencies: Set<string>;
	content: string;
}

const ENTRYPOINT_FILENAME: string = 'main.ts';
class HotReloadingCompiler {
	hotReloadPath: string;
	rootFilePath: string;
	dependencyTree: { [key: string]: FileInfo[] | undefined };
	sourceFiles: { [key: string]: FileInfo };

	/** rootFilePath is the typescript file which hold the _start function used as the entry point for hot reloaded code execution. */
	constructor(hotReloadPath: string) {
		this.hotReloadPath = path.join(process.cwd(), hotReloadPath);
		this.rootFilePath = path.join(this.hotReloadPath, ENTRYPOINT_FILENAME);
		this.dependencyTree = {};
		this.sourceFiles = {};
	}

	private _isImportTypeOnly(importDeclaration: ts.ImportDeclaration): boolean {
		if (!importDeclaration.importClause) {
			return false;
		}
		const importClause = importDeclaration.importClause;
		if (importClause.isTypeOnly) {
			return true;
		}
		if (!importClause.namedBindings || !importClause.namedBindings.elements) {
			return false;
		}
		return importClause.namedBindings.elements.every((elem) => elem.isTypeOnly);
	}

	private _isHotReloadedModule(
		folderPath: string,
		importDeclaration: ts.ImportDeclaration
	): boolean {
		// It will be "" if paths are the same, start with ".." if it's not a descendant
		const moduleName = importDeclaration.moduleSpecifier.text;
		if (!moduleName.startsWith('.')) {
			// A module which is not declared with relative path (starting from ".") is a module stored in node_modules, hot reloaded modules can't be stored in node_modules.
			return false;
		}
		const modulePath = path.join(folderPath, moduleName);
		const relativePath = path.relative(this.hotReloadPath, modulePath);
		// Relative is ""
		return !relativePath || (!relativePath.startsWith('..') && !path.isAbsolute(relativePath));
	}

	private _isImportIncluded(folderPath: string, importDeclaration: ts.ImportDeclaration) {
		return (
			this._isHotReloadedModule(folderPath, importDeclaration) &&
			!this._isImportTypeOnly(importDeclaration)
		);
	}

	private _getCodeAndDependencies(folderPath: string, codeContent: string): [string, Set<string>] {
		const sourceFile = ts.createSourceFile('_', codeContent, ts.ScriptTarget.ESNext);
		/*
      // To check if a file/directory exists
      // fs.existsSync(filePath)
      // It will be "" if paths are the same, start with ".." if it's not a descendant
      const relative = path.relative(parentPath, childPath);
      return relative && !relative.startsWith('..') && !path.isAbsolute(relative);
    */
		const importDeclarations: ts.ImportDeclaration[] = sourceFile.statements.filter((statement) =>
			ts.isImportDeclaration(statement)
		);
		// elem.kind === ts.SyntaxKind.ImportDeclaration
		if (importDeclarations.length === 0) {
			return [codeContent, new Set()];
		}
		let realCode = '';
		let lastEnd = 0;
		for (const importDeclaration of importDeclarations) {
			realCode += codeContent.substring(lastEnd, importDeclaration.pos);
			lastEnd = importDeclaration.end;
		}
		realCode += codeContent.substring(lastEnd, codeContent.length);

		const dependencies = new Set(
			importDeclarations
				.filter((importDeclaration) => this._isImportIncluded(folderPath, importDeclaration))
				.map((importDeclaration) => {
					let filename = importDeclaration.moduleSpecifier.text;
					if (!filename.endsWith('.ts')) {
						filename += '.ts';
					}
					return path.join(folderPath, filename);
				})
		);

		return [realCode, dependencies];
	}

	private _stripExportKeywords(codeLines: string): string {
		return codeLines
			.split('\n')
			.map((line: string) => {
				const trimmedLine = line.trimStart();
				// Whitespace is kept for better readbility when debugging.
				const leadingWhitespace = line.substring(0, line.length - trimmedLine.length);
				const strippedLine = trimmedLine.replace(/^export /, '');
				return leadingWhitespace + strippedLine;
			})
			.join('\n');
	}

	/**
	 * Read and save the source code and dependencies of a file included in the hot reloaded code
	 */
	registerSourceCode(filePath: string) {
		const folderPath = path.dirname(filePath);
		const originalCode = readFileSync(filePath).toString();

		const [realCode, dependencies]: [string, Set<string>] = this._getCodeAndDependencies(
			folderPath,
			originalCode
		);
		const strippedRealCode = this._stripExportKeywords(realCode);
		const sourceFileInfo = {
			content: strippedRealCode,
			dependencies: dependencies
		};
		this.sourceFiles[filePath] = sourceFileInfo;
		for (const dependency of dependencies) {
			if (!this.dependencyTree.hasOwnProperty(dependency)) {
				this.dependencyTree[dependency] = [sourceFileInfo];
			} else {
				this.dependencyTree[dependency]!.push(sourceFileInfo);
			}
			if (!this.sourceFiles.hasOwnProperty(dependency)) {
				// Recursively register source files specified by the //include directive.
				this.registerSourceCode(dependency);
			}
		}
	}

	findCircularDependency(
		nodeFilePath: string | null = null,
		visitedNodes: Set<string> = new Set(),
		importedNodes: Set<string> = new Set()
	): [string, string] | null {
		nodeFilePath ??= this.rootFilePath;
		visitedNodes.add(nodeFilePath);
		importedNodes.add(nodeFilePath);
		let result: [string, string] | null = null;
		const node = this.sourceFiles[nodeFilePath];
		// Use DFS for this (stack of dependencies + stack of already imported modules ?)
		for (const dependency of node.dependencies) {
			if (importedNodes.has(dependency)) {
				// CIRCULAR DEPENDENCY DETECTED
				return [nodeFilePath, dependency];
			}
			if (visitedNodes.has(dependency)) {
				continue;
			}
			result = this.findCircularDependency(dependency, visitedNodes, importedNodes);
			if (result) {
				break;
			}
		}
		importedNodes.delete(nodeFilePath);
		return result;
	}

	/** Clear all circular dependencies by breaking its cycle */
	clearCircularDependencies() {
		let circularDependency;
		while ((circularDependency = this.findCircularDependency()) !== null) {
			const [filePath, dependency] = circularDependency;
			// Break the circular dependency
			this.sourceFiles[filePath].dependencies.delete(dependency);
		}
	}

	/** Precompile the hot reloaded code its precompiled version after executing the //include directives.
	 * @throws {Error} Throws an error if an //include attempts to open/read a file it cannot read.
	 * Returns the precompiled typescript code for hot reloading.
	 */
	precompile(): string {
		this.registerSourceCode(this.rootFilePath);
		this.clearCircularDependencies();

		const unloadedFiles = new Set(Object.keys(this.sourceFiles));
		const newlyLoadedFiles: string[] = [];
		let outputCode = '';

		// This code doesn't handle circular dependencies (handle this later)
		// Right now circular dependencies result in an infinite loop
		while (unloadedFiles.size > 0) {
			for (const filePath of unloadedFiles) {
				const { dependencies, content } = this.sourceFiles[filePath];

				if (dependencies.size === 0) {
					outputCode += content + '\n';
					newlyLoadedFiles.push(filePath);
					const dependencyTree = this.dependencyTree[filePath] ?? [];
					dependencyTree.forEach((fileInfo) => {
						fileInfo.dependencies.delete(filePath);
					});
				}
			}
			for (const filePath of newlyLoadedFiles) {
				unloadedFiles.delete(filePath);
			}
			newlyLoadedFiles.length = 0;
		}
		return outputCode;
	}
}

interface runOptions {
	updateInterval?: number;
	hotReloaderPath?: string;
}

export const HotReload = new (class {
	private _counter: number;
	private _isTestRunning: boolean;
	private _isRunning: boolean;
	private _errorList: TestInfoError[];
	private _errorCount: number;
	private _currentCode: string;
	private _currentCompilationError: string | undefined;
	private _uniqueValue: any;

	constructor() {
		this._counter = 0;
		this._isTestRunning = true;
		this._isRunning = true;
		this._errorList = []; // Snapshot of the last registered TestInfo.errors
		this._errorCount = 0;
		this._currentCode = '';
		this._currentCompilationError = undefined;
		this._uniqueValue = 'SomeNonce';
	}

	*getLongIterator() {
		for (let i = 0; i < 256; i++) {
			yield i;
		}
	}

	getIsTestRunning(): boolean {
		return this._isTestRunning;
	}

	getIsRunning(): boolean {
		return this._isRunning;
	}

	getTestDescribeName(): string {
		return `${++this._counter}`;
	}

	getCount(): number {
		return this._counter;
	}

	doStopTest() {
		this._isTestRunning = false;
	}

	doStart() {
		this._isRunning = true;
	}

	doStop(uniqueValue: any) {
		if (uniqueValue === this._uniqueValue) {
			return;
		}
		this._uniqueValue = uniqueValue;
		this._isRunning = false;
	}

	async doDisplayErrors(testInfo: TestInfo) {
		// Bad performances: O(TestInfo.length*this._errorList.length), but whatever
		testInfo.errors.forEach((error) => {
			if (this._errorList.indexOf(error) === -1) {
				console.log(`[ERROR:${++this._errorCount}] ${error.message}`);
			}
		});
		this._errorList = [...testInfo.errors];
	}

	/** Write this docstring */
	async doRun(
		functionArgs: { [key: string]: any } = {},
		testInfo: TestInfo,
		options: runOptions = {}
	) {
		const compiler = new HotReloadingCompiler(options.hotReloaderPath ?? './tests/hot-reload');
		let bundledCode = '';
		try {
			bundledCode = compiler.precompile();
		} catch (e) {
			const currentError = e.toString();
			if (this._currentCompilationError !== currentError) {
				console.log(`[COMPILATION_ERROR] Due to import | ${currentError}`);
				this._currentCompilationError = currentError;
			}
			return;
		}
		// This makes the eval return the _start function so that we can call it.
		bundledCode += '\n(async(args)=>_start(args))';
		if (bundledCode === this._currentCode) {
			return;
		}
		this._currentCode = bundledCode;

		const finalCode = ts.transpileModule(bundledCode, {
			compilerOptions: { module: ts.ModuleKind.CommonJS }
		}).outputText;

		try {
			// entryPoint is the _start function as defined in the main.ts of the Hot Reloader path.
			const entryPoint: (args: any) => Promise<void> = eval(finalCode);
			// The argument passed to HotReload.doRun({...}) is passed down to the _start function.
			await entryPoint(functionArgs);
		} catch (e) {
			console.log(`[CODE_ERROR] ${e.message}`);
		}
		await this.doDisplayErrors(testInfo);
		await new Promise((res) => setTimeout(res, options.updateInterval ?? 100));
	}
})();

// The type of the allFixtures argument will have to be set in the future.
export async function hotReloadInTest(
	test: TestType<any, any>,
	_expect: typeof expect,
	testInfo: TestInfo,
	allFixtures: { [key: string]: any },
	data: { [key: string]: any } = {},
	expectTimeout: number = 3_000
) {
	test.setTimeout(3600_000);
	for (let counter = 0; HotReload.getIsRunning(); counter++) {
		const newExpect = _expect.configure({ timeout: expectTimeout });
		await HotReload.doRun(
			{
				test: test,
				_except: _expect,
				// We use the soft version of expect to prevent false assertions to stop the currently running test.
				expect: newExpect.soft,
				allFixtures: allFixtures,
				counter: counter,
				HotReload: HotReload,
				data: data
			},
			testInfo
		);
	}
}

export function hotReloadLoop(expectTimeout: number = 3_000) {
	for (const _ of HotReload.getLongIterator()) {
		test.describe(HotReload.getTestDescribeName(), () => {
			test.beforeEach(async () => {
				test.setTimeout(3600_000);
				HotReload.doStart();
				if (!HotReload.getIsTestRunning()) {
					test.skip();
				}
			});
			test('Hot-reloaded test', async ({ page, allFixtures }, testInfo) => {
				for (let counter = 0; HotReload.getIsRunning(); counter++) {
					const newExpect = expect.configure({ timeout: expectTimeout });
					await HotReload.doRun(
						{
							test: test,
							_except: expect,
							// We use the soft version of expect to prevent false assertions to stop the currently running test.
							expect: newExpect.soft,
							allFixtures: allFixtures,
							counter: counter,
							HotReload: HotReload
						},
						testInfo
					);
				}
			});
		});
	}
}

interface ArgsType {
	test: TestType<any, any>;
	expect: typeof expect;
	allFixtures: AllFixtures;
	counter: number;
	HotReload: typeof HotReload;
	data?: { [key: string]: any };
}

export type EntryPoint = (args: ArgsType) => Promise<void>;
