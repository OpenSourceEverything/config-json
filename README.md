# config-json

Minimal config loader and validator.

## Commands

- `config-json init [--template base] [--dest .] [--force]`
  - Copies `templates/base/config` into `<dest>/config`.
  - Refuses overwrite unless `--force`.
- `config-json validate [--root .] [--no-validate-per-file] [--write-wrapped-effective]`
  - Discovers domains (`active.txt` folders), loads active JSON, merges domains in lexical domain-id order.
  - Optional root selector can override per-domain active selection (`config/active.txt` -> `config/<profile>.json` map).
  - When a root selector map is present, it must include every discovered domain-id (no implicit fallback).
  - Merges overrides from `config/active-overrides.txt` (JSON filename list) in listed order; falls back to `config/overrides.json` when selector is absent.
  - Writes `config/config.json`.
  - Optional: also writes `config/config.wrapped.json` (domain-id namespaced shape) when `--write-wrapped-effective` is set.
  - Validates domain selector files (`<domain>/active.txt`) for strict single `<profile>.json` filename format.
  - Validates each `*.json` file in each domain folder in overlay mode (default on).
  - Validates merged effective config against `config/config.schema.json`.
  - Exits nonzero on any error.
- `config-json resolve [--root .] [--format text|json] [--include-effective] [--wrap-domains]`
  - Prints each resolved domain id and the selected active file.
  - Useful for debugging root-profile maps vs per-domain `active.txt`.
  - `--wrap-domains` emits the effective config using domain folder names as object namespaces.

## Validate-Per-File (Default On)

Per-file validation ignores `required` but still enforces type/enum/range/additionalProperties. Disable with `--no-validate-per-file`.

## Rules

- Domain = any folder containing `active.txt`.
- Active file precedence:
  - pointer files (`config/active.txt`, `<domain>/active.txt`) contain exactly one active value (blank lines and `#` comments allowed)
  - root selector value is one filename (for example `profile.json`)
  - if present, load `config/<that filename>` as `{ "<domain-id>": "<profile>.json" }`
  - that one root map file can define active selections for many modules/domains
  - if root selector is present, all discovered domains must be explicitly mapped (or validation fails)
  - if root selector is absent, each domain uses `<domain>/active.txt`
- Base merge order = lexical by full domain id.
- Overrides precedence:
  - if `config/active-overrides.txt` exists: parse JSON array of filenames, load each `config/<filename>` in listed order, merge in-order
  - else: optional single file `config/overrides.json`
- `deep_merge` = object+object recurse, else override replaces.
- Unknown key behavior is defined by your schema (`additionalProperties`).

### Precedence (highest wins)

1. `config/active-overrides.txt` list entries (or `config/overrides.json` fallback)
2. Base from domain active selections (root map + per-domain `active.txt`)
3. Defaults (if your app applies defaults before/after merge)
