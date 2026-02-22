# config-json

Minimal config loader and validator.

## Commands

- `config-json init [--template base] [--dest .] [--force]`
  - Copies `templates/base/config` into `<dest>/config`.
  - Refuses overwrite unless `--force`.
- `config-json validate [--root .] [--no-validate-per-file]`
  - Discovers domains (`active.txt` folders), loads active JSON, merges domains in lexical domain-id order.
  - Optional root selector can override per-domain active selection (`config/active.txt` -> `config/<profile>.json` map).
  - Merges overrides from `config/active-overrides.txt` (JSON filename list) in listed order; falls back to `config/overrides.json` when selector is absent.
  - Writes `config/config.json`.
  - Validates each `*.json` file in each domain folder in overlay mode (default on).
  - Validates merged effective config against `config/config.schema.json`.
  - Exits nonzero on any error.

## Validate-Per-File (Default On)

Per-file validation ignores `required` but still enforces type/enum/range/additionalProperties. Disable with `--no-validate-per-file`.

## Rules

- Domain = any folder containing `active.txt`.
- Active file precedence:
  - `config/active.txt` contains exactly one filename (for example `profile.json`)
  - if present, load `config/<that filename>` as `{ "<domain-id>": "<profile>.json" }`
  - that one root map file can define active selections for many modules/domains
  - mapped domains use map filename
  - unmapped domains use `<domain>/active.txt`
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
