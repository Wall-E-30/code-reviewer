/**
 * Aion Code Reviewer VS Code Extension (APP-03)
 * Provides local git staged diff inspection, inline diagnostic squiggles,
 * and 1-click QuickFix code suggestion actions.
 */

const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');

let diagnosticCollection;
let outputChannel;

/**
 * Execute the Aion CLI and return parsed JSON findings.
 * @param {string[]} args
 * @param {string} cwd
 * @returns {Promise<Array<Object>>}
 */
function runAion(args, cwd) {
    return new Promise((resolve, reject) => {
        const config = vscode.workspace.getConfiguration('aion');
        const executable = config.get('executablePath', 'aion');

        cp.execFile(executable, args, { cwd: cwd, maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
            if (error && !stdout) {
                // If the binary isn't in PATH or exited with error without output
                return reject(new Error(stderr || error.message));
            }
            try {
                const findings = JSON.parse(stdout || '[]');
                resolve(Array.isArray(findings) ? findings : []);
            } catch (parseErr) {
                if (stdout.includes('[aion] No actionable issues detected')) {
                    return resolve([]);
                }
                reject(new Error(`Failed to parse Aion CLI output: ${stdout}\n${stderr}`));
            }
        });
    });
}

/**
 * Update the VS Code DiagnosticCollection with findings.
 * @param {Array<Object>} findings
 * @param {string} workspaceRoot
 */
function updateDiagnostics(findings, workspaceRoot) {
    diagnosticCollection.clear();

    const fileMap = new Map();

    for (const item of findings) {
        const fullPath = path.isAbsolute(item.file_path)
            ? item.file_path
            : path.join(workspaceRoot, item.file_path);

        if (!fileMap.has(fullPath)) {
            fileMap.set(fullPath, []);
        }

        const line = Math.max(0, (item.line_number || 1) - 1);
        const range = new vscode.Range(line, 0, line, 1000);

        let severity = vscode.DiagnosticSeverity.Warning;
        const cat = (item.category || '').toLowerCase();
        const sev = (item.severity || '').toLowerCase();

        if (cat === 'security' || sev === 'critical') {
            severity = vscode.DiagnosticSeverity.Error;
        } else if (sev === 'info' || cat === 'style') {
            severity = vscode.DiagnosticSeverity.Information;
        }

        const message = `[Aion ${cat.toUpperCase()}] ${item.comment}`;
        const diagnostic = new vscode.Diagnostic(range, message, severity);
        diagnostic.source = 'Aion';
        diagnostic.code = item.rule_id || item.category || 'review';

        // Custom property stored for CodeAction QuickFix provider
        diagnostic._aionSuggestion = item.suggestion;
        diagnostic._aionItem = item;

        fileMap.get(fullPath).push(diagnostic);
    }

    for (const [filePath, diagnostics] of fileMap.entries()) {
        const uri = vscode.Uri.file(filePath);
        diagnosticCollection.set(uri, diagnostics);
    }
}

/**
 * Extension activation entry point.
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    diagnosticCollection = vscode.languages.createDiagnosticCollection('aion');
    outputChannel = vscode.window.createOutputChannel('Aion Code Reviewer');
    context.subscriptions.push(diagnosticCollection);
    context.subscriptions.push(outputChannel);

    // 1. Command: aion.reviewStaged
    const reviewStagedCmd = vscode.commands.registerCommand('aion.reviewStaged', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('Aion: No open workspace folder found.');
            return;
        }

        const rootPath = workspaceFolders[0].uri.fsPath;
        const config = vscode.workspace.getConfiguration('aion');
        const minConf = config.get('minConfidence', 0.70);
        const maxComments = config.get('maxComments', 5);

        vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Aion: Reviewing staged git changes...',
                cancellable: false,
            },
            async () => {
                try {
                    const findings = await runAion(
                        ['review', '--staged', '--json', '--min-confidence', String(minConf), '--max-comments', String(maxComments)],
                        rootPath
                    );

                    updateDiagnostics(findings, rootPath);

                    if (findings.length === 0) {
                        vscode.window.showInformationMessage('✨ Aion: No issues detected in staged changes!');
                    } else {
                        vscode.window.showWarningMessage(
                            `🔍 Aion: Found ${findings.length} actionable review issue(s). Check Problems panel.`
                        );
                    }
                } catch (err) {
                    vscode.window.showErrorMessage(`Aion review failed: ${err.message}`);
                }
            }
        );
    });

    // 2. Command: aion.reviewCurrentFile
    const reviewFileCmd = vscode.commands.registerCommand('aion.reviewCurrentFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showInformationMessage('Aion: No active file to review.');
            return;
        }

        const filePath = editor.document.uri.fsPath;
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const rootPath = (workspaceFolders && workspaceFolders.length > 0)
            ? workspaceFolders[0].uri.fsPath
            : path.dirname(filePath);

        try {
            const findings = await runAion(['review', '--file', filePath, '--json'], rootPath);
            updateDiagnostics(findings, rootPath);
            if (findings.length === 0) {
                vscode.window.showInformationMessage('✨ Aion: No issues found in current file.');
            } else {
                vscode.window.showWarningMessage(`🔍 Aion: ${findings.length} issue(s) found in current file.`);
            }
        } catch (err) {
            vscode.window.showErrorMessage(`Aion file review failed: ${err.message}`);
        }
    });

    // 3. Command: aion.showConventions
    const showConventionsCmd = vscode.commands.registerCommand('aion.showConventions', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        const rootPath = (workspaceFolders && workspaceFolders.length > 0)
            ? workspaceFolders[0].uri.fsPath
            : process.cwd();

        const config = vscode.workspace.getConfiguration('aion');
        const executable = config.get('executablePath', 'aion');

        cp.execFile(executable, ['conventions', '--list'], { cwd: rootPath }, (err, stdout, stderr) => {
            outputChannel.clear();
            if (err) {
                outputChannel.appendLine(`Error: ${stderr || err.message}`);
            } else {
                outputChannel.appendLine(stdout);
            }
            outputChannel.show(true);
        });
    });

    // 4. QuickFix CodeActionProvider
    const codeActionProvider = vscode.languages.registerCodeActionsProvider(
        '*',
        {
            provideCodeActions(document, range, context) {
                const actions = [];

                for (const diagnostic of context.diagnostics) {
                    if (diagnostic.source === 'Aion' && diagnostic._aionSuggestion) {
                        const action = new vscode.CodeAction(
                            '💡 Aion: Apply suggested fix',
                            vscode.CodeActionKind.QuickFix
                        );
                        action.diagnostics = [diagnostic];
                        action.isPreferred = true;

                        const edit = new vscode.WorkspaceEdit();
                        const line = diagnostic.range.start.line;
                        const lineRange = document.lineAt(line).range;
                        edit.replace(document.uri, lineRange, diagnostic._aionSuggestion);

                        action.edit = edit;
                        actions.push(action);
                    }
                }

                return actions;
            },
        },
        {
            providedCodeActionKinds: [vscode.CodeActionKind.QuickFix],
        }
    );

    // 5. Auto-review on file save (if enabled in settings)
    const onSaveListener = vscode.workspace.onDidSaveTextDocument((document) => {
        const config = vscode.workspace.getConfiguration('aion');
        if (config.get('autoReviewOnSave', false)) {
            vscode.commands.executeCommand('aion.reviewCurrentFile');
        }
    });

    context.subscriptions.push(reviewStagedCmd);
    context.subscriptions.push(reviewFileCmd);
    context.subscriptions.push(showConventionsCmd);
    context.subscriptions.push(codeActionProvider);
    context.subscriptions.push(onSaveListener);
}

/**
 * Extension deactivation cleanup.
 */
function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
        diagnosticCollection.dispose();
    }
}

module.exports = {
    activate,
    deactivate,
    runAion,
    updateDiagnostics,
};

