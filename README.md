# config-json

Minimal config loader and validator.

## Commands

- `config-json init [--template base] [--dest .] [--force]`
  - Copies `templates/base/config` into `<dest>/config`.
  - Refuses overwrite unless `--force`.
- `config-json validate [--root .] [--no-validate-per-file]`
  - Discovers domains (`active.txt` folders), loads active JSON, merges domains in lexical domain-id order.
  - Optional root selector can override per-domain active selection (`config/active.txt` -> `config/active.<name>.json` map).
  - Merges optional `config/overrides.json` last.
  - Writes `artifacts/effective-config.json`.
  - Validates each `*.json` file in each domain folder in overlay mode (default on).
  - Validates merged effective config against `config/config.schema.json`.
  - Exits nonzero on any error.

## Validate-Per-File (Default On)

Per-file validation ignores `required` but still enforces type/enum/range/additionalProperties. Disable with `--no-validate-per-file`.

## Rules

- Domain = any folder containing `active.txt`.
- Active file precedence:
  - if `config/active.txt` exists, load `config/<that filename>` as `{ "<domain-id>": "<profile>.json" }`
  - mapped domains use map filename
  - unmapped domains use `<domain>/active.txt`
- Base merge order = lexical by full domain id.
- Overrides = optional single file `config/overrides.json`, merged last.
- `deep_merge` = object+object recurse, else override replaces.
- Unknown key behavior is defined by your schema (`additionalProperties`).
