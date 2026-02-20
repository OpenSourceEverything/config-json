# Config Layout (Canonical)

## Summary

Deterministic, json-based domain config merge with one root override.
Root `config/config.schema.json` is the app schema (include `"$schema"` there).

### Structure Example

```text
config/
  config.schema.json
  active.txt
  active.dev.json
  overrides.json
  app/
    active.txt
    dev.json
  db/
    active.txt
    local.json
  simulators/
    ble/
      active.txt
      dev.json
```

## CLI

- `config-json init [--template base] [--dest .] [--force]`
  - copies `templates/base/config` to `<dest>/config`
  - refuses overwrite unless `--force`
- `config-json validate [--root .] [--no-validate-per-file]`
  - merges + validates
  - writes `artifacts/effective-config.json`

## Rules

### Domain Discovery

- Domain = any folder containing `active.txt`.
- Domain id = folder path relative to `config/` using `/` (ex: `simulators/ble`).
- Active file precedence:
  - if root `config/active.txt` exists, load `config/<that filename>` as `{ "<domain-id>": "<profile>.json" }`
  - mapped domains use mapped filename
  - unmapped domains use `<domain>/active.txt`
- Base merge order = lexical by full domain id.

### Schema

- Only `config/config.schema.json` is used.
- Unknown key behavior is defined by schema (`additionalProperties`).

### Overrides

- Optional single file: `config/overrides.json`.
- Merged last: `effective = deep_merge(base, overrides)`.

### deep_merge

- object + object -> recurse.
- else override replaces (scalar, array, null, or type mismatch).
- missing key in override keeps base value.

### Validate Contract

- `active.txt` is readable for each domain.
- referenced active JSON exists.
- selected JSON parses.
- per-file pass (default on):
  - for each domain folder, validate each `*.json` in that folder
  - overlay mode against `config/config.schema.json` (ignore `required` only)
  - still enforce type/enum/range/additionalProperties
  - disable with `--no-validate-per-file`
- effective config validates normally against `config/config.schema.json`.

## Resolution Algorithm

1) Discover all domain folders (`active.txt`).
2) Sort domain ids lexically.
3) If root `config/active.txt` exists: load `config/<that filename>` map.
4) For each domain in order: resolve active filename (root map or domain active.txt), load JSON, `base = deep_merge(base, c)`.
5) If `config/overrides.json` exists: load and merge last.
6) Write `artifacts/effective-config.json`.
7) Run per-file overlay validation (default on).
8) Run effective-config validation.

### Nested Example

`config/simulators/ble/active.txt`:

```text
dev.json
```

Example lexical order:

```text
app -> db -> simulators/ble
```
