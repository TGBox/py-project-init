# Changelog

## SemVer v3.0.1

- 2026-10-28 (a3d3ebc): feat: add a more fine granular configuration option for the git hook lifecycle
- 2026-10-26 (ff1a42b): Merge pull request #4 from TGBox/smart-tests
- 2026-10-26 (4a8c5cf): fix: change pre push hook templates to check for changed code files before starting a full test suite
- 2026-10-26 (0342028): Merge pull request #3 from TGBox/ai-decide
- 2026-10-26 (d34165d): fix: fix deprecated default model selection for gemini, feat: add manual key verification button, add automated saving of the key on first successful call with direct feedback via info dialog
- 2026-10-26 (b71e11c): feat: add new ai advisor where the user can enter and safely store ai keys for local or external ai models to provide advice on the selection of an ai framework or a project title, add ui integration, add testsuites
- 2026-10-26 (50478ce): Merge pull request #2 from TGBox/github
- 2026-10-26 (1b9de17): feat: add option to directly create the external repo on github as well, utilizing PATs, feat: allow for branching in the same way as for gitlab, feat: add cli options for all new actions, feat: add new tests and update README.md
- 2026-10-26 (d9c57c1): feat: add new plan for github integration
- 2026-10-25 (8345867): fix: adjust project templates to remove unused import statements from the file templates, to avoid an initial push directly failing the linter check in an external repo
- 2026-10-24 (3381342): feat: add new unity game dev template
- 2026-10-20 (900fa79): fix: update git hooks to show the semver before bumping it and again afterwards so the user sees exactly, what the current version is
- 2026-10-17 (2417341): fix!: fix templates generating code that does not pass the provided linter and typecheck tests after initializing
- 2026-10-17 (233e93f): fix: fix incorrect formatting in web frontend template
- 2026-10-17 (7bcdc08): feat: add new templates for multiple different program types, update and specify the agent rules templates to match the new formats, update the script commands for the different types and languages
- 2026-10-17 (f7b54c0): feat: add new planning documents
- 2026-10-16 (ebb38e7): fix: fix project.scripts block in python project config having too many empty lines
- 2026-10-16 (fcd063e): fix: remove problematic additional check against missing key authority in our gitlab certificate authority
- 2026-10-16 (8f0e920): fix: update uv.lock file
- 2026-10-16 (e605be6): feat!: add new feature to create gitlab repositories directly and prevent empty ones
- 2026-10-16 (8745192): fix: hook changes
- 2026-10-15 (0f5816e): fix!: fix git hooks not accounting for correct semver bumping on projects that aren't python
- 2026-10-15 (cb10ef6): Merge pull request #1 from TGBox/develop
- 2026-10-15 (aadbfc5): feat: add new todo.txt file with a new todo
- 2026-10-15 (b3dc928): feat: test commit from powershell
- 2026-10-13 (18517c3): feat(templates)!: fix wrongfully configured template files for setup, fix(output): fix output to inform user what errors have occurred
- 2026-10-11 (515d235): fix(uv): add changed lock file
- 2026-10-11 (956e7ff): fix(toml): bump semver

## SemVer v3.0.0

- 2026-10-11 (7aa191d): fix(preview)!: live preview is now working correctly
- 2026-10-11 (aa47622): fix: update uv.lock with new specs
- 2026-10-11 (73325af): fix: update semver manually

## SemVer v2.0.1

- 2026-10-11 (1c682fc): fix(config): new projects are now not getting their dashes replaced by underscores in the script names and subfolders, feat!(scripts): added new default selection of scripts to include in the newly generated projects
- 2026-10-10 (e9ffd5a): fix(hooks): optimize hook workflow to prevent a semver bump when a commit message was configured incorrectly
- 2026-10-10 (f030481): fix(changelog): add newly generated changelog file

## SemVer v2.0.0

- 2026-10-10 (2fe1390): feat: apply post upgrade to own project repo

## SemVer v1.0.0

- 2026-10-11 (ec11295): fix!: hook logic adjustments to allow for semver bumps as major, adjust spec file for new version
- 2026-10-10 (c08fd7d): feat(hooks): update post-commit hook template and add new option in the setup to configure automated tagging in git
- 2026-10-10 (bb0ac39): fix generation of the agents.md file so that it adheres to markdownlint standards
- 2026-10-09 (4137bb3): changed agent reference skill files
- 2026-10-09 (66bc8fa): feat(ui): optimize GUI layout with 2-column master-detail splitter, tabs, and live inspector card
- 2026-10-09 (ce708f3): feat: add explicit GPLv3 license warning modal and switch option for PyQt6
- 2026-10-09 (951ad51): feat: add live preview, IDE launchers, headless CLI, retrofit mode, and template creator
- 2026-10-09 (9a70b58): feat(hooks): integrate comprehensive client-side git hooks suite and tests
- 2026-10-09 (8270419): bump semver

## SemVer v0.1.0

- 2026-10-09 (ee86c65): big rework of the app, add git hook selections, add agents rules and skills for modular selection, optimize command order
- 2026-09-27 (d2c90dd): update readme file
- 2026-09-27 (cebe9b0): docs: add comprehensive README.md
- 2026-09-27 (984b0dd): update spec file
- 2026-09-27 (ed6efe0): refactor: apply ponytail audit optimizations (streamline generator, native Qt explorer, remove unused code)
- 2026-09-27 (5afd565): feat: implement nice-to-have features (dark theme, QSettings, cancel, custom templates, fullscreen)
- 2026-09-27 (b5f63e7): fix user feedback not clear, fix project name character validation, fix hook console output, fix template descriptions
- 2026-09-27 (f4760dd): fix missing template files, fix conditional configs
- 2026-09-27 (ea73bfb): create first draft with some templates
- 2026-09-27 (61b96dd): initial commit
