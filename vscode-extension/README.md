# Nova Language Support for VS Code

This local extension recognizes `.nova` files anywhere in VS Code. It provides:

- Automatic Nova language mode for every `.nova` file.
- Syntax highlighting for Nova's implemented keywords, strings, numbers, comments, variables, functions, built-ins, operators, lists, dictionaries, and blocks.
- A Nova Explorer file icon through the **Nova Icons** file icon theme.
- A separate `icons/nova-logo.png` Marketplace logo; the Explorer icon remains `icons/nova-file.svg`.
- The optional **Nova Night** color theme, tuned for the Nova TextMate scopes.

It intentionally does not add highlighting for syntax Nova does not implement (for example classes, imports, `break`, `continue`, or `match`).

## Package and install on Windows PowerShell

From this `vscode-extension` directory, package it with the VS Code Extension Manager. `npx` downloads and runs `vsce` for this command only, so no global npm package is required.

```powershell
cd E:\nova-lang\vscode-extension
npx --yes @vscode/vsce package --allow-missing-repository
code --install-extension .\nova-language-dex-0.1.1.vsix
```

If `npx` is unavailable, install `vsce` once and use the same package command:

```powershell
npm install --global @vscode/vsce
vsce package --allow-missing-repository
code --install-extension .\nova-language-dex-0.1.1.vsix
```

## Publish to the VS Code Marketplace

The extension is configured for the Marketplace publisher `DexterNova`. After creating a Marketplace Personal Access Token with Marketplace **Manage** scope, set it in PowerShell and publish from this directory:

```powershell
cd E:\nova-lang\vscode-extension
$env:VSCE_PAT = "<your-marketplace-personal-access-token>"
vsce publish --pat $env:VSCE_PAT
```

`vsce` reads the `DexterNova` publisher from `package.json`; do not replace it with the local project name.

Restart VS Code or run **Developer: Reload Window** after installation.

## Enable the included icon and color theme

VS Code lets users choose one file icon theme and one color theme globally. After installing:

1. Run **Preferences: File Icon Theme** and choose **Nova Icons**.
2. Optionally run **Preferences: Color Theme** and choose **Nova Night**.

The language mode itself needs no manual selection: creating or opening any `hello.nova` file in any project automatically selects **Nova**. With **Nova Icons** selected, that file also receives the Nova Explorer icon.

## Test without installing

Open `E:\nova-lang\vscode-extension` in VS Code and press `F5`. The Extension Development Host opens with this extension loaded. Open a `.nova` file and confirm the status bar says **Nova**, syntax is highlighted, and the Explorer shows the Nova icon after selecting **Nova Icons**.
