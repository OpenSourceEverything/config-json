# Config Layout (Canonical)

## Summary

Deterministic, json-based domain config merge with one root override.
Root `config/config.schema.json` is the app schema (include `"$schema"` there).

### Structure Example

```text
config/
  config.schema.json
  active.txt
  profile.json
  profile.2.json
  active-overrides.txt
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
  - writes `config/config.json`

## Rules

### Domain Discovery

- Domain = any folder containing `active.txt`.
- Domain id = folder path relative to `config/` using `/` (ex: `simulators/ble`).
- Active file precedence:
  - `config/active.txt` contains exactly one filename (for example `profile.json`)
  - if root selector exists, load `config/<that filename>` as `{ "<domain-id>": "<profile>.json" }`
  - that one map file can define active files for multiple domains/modules
  - mapped domains use mapped filename
  - unmapped domains use `<domain>/active.txt`
- Base merge order = lexical by full domain id.

### Schema

- Only `config/config.schema.json` is used.
- Unknown key behavior is defined by schema (`additionalProperties`).

### Overrides

- If `config/active-overrides.txt` exists: it must be a JSON array of filenames.
- Load each `config/<filename>` in listed order and merge in-order.
- If selector is absent, optional fallback is `config/overrides.json`.
- Overrides always apply on top of the active-selected base.

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
3) If root `config/active.txt` exists: read one filename, then load `config/<that filename>` map.
4) For each domain in order: resolve active filename (root map or domain active.txt), load JSON, `base = deep_merge(base, c)`.
5) Resolve overrides:
   - if `config/active-overrides.txt` exists: load listed files in-order and merge in-order
   - else if `config/overrides.json` exists: load once
6) Merge overrides last.
7) Write `config/config.json`.
8) Run per-file overlay validation (default on).
9) Run effective-config validation.

### Nested Example

`config/simulators/ble/active.txt`:

```text
dev.json
```

Example lexical order:

```text
app -> db -> simulators/ble
```
