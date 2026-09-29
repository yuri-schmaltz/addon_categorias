# Extension & Add-on Categories

> **Categorize, organize, and filter Blender add-ons and extensions with custom tags, bulk controls, and JSON export/import.**

[![Blender](https://img.shields.io/badge/Blender-4.2%2B-orange?logo=blender)](https://blender.org)
[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green)]()

A power-user companion for the **Edit → Preferences → Add-ons** and **Get Extensions** tabs in Blender 4.2+. It adds a category-based organizer that works on top of the native add-on browser without replacing it.

---

## Table of contents

- [Why this add-on?](#why-this-add-on)
- [Features](#features)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Default categories](#default-categories)
- [Auto-tagging heuristic](#auto-tagging-heuristic)
- [User interface](#user-interface)
- [JSON export / import](#json-export--import)
- [Operators reference](#operators-reference)
- [Preferences storage](#preferences-storage)
- [Compatibility](#compatibility)
- [Development](#development)
- [Testing](#testing)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Credits](#credits)

---

## Why this add-on?

Once you accumulate more than 30 add-ons and start mixing in the new **Extensions** platform, the default Preferences UI becomes a wall of text. You waste seconds scanning for the one tool you need, lose track of which extensions are installed but disabled, and have no way to bulk-toggle related add-ons together.

**Extension & Add-on Categories** gives you:

- A **persistent classification** layer over both legacy add-ons and modern extensions.
- **One-click bulk enable/disable** scoped to a category.
- **Search + status filters** that survive between sessions.
- **JSON backup/restore** so you can sync the same taxonomy across machines or share it with collaborators.

It does not modify the underlying add-ons, and it never disables itself when running bulk operations.

---

## Features

| Area | Capability |
|---|---|
| **Categories** | 10 factory categories + unlimited user-defined custom ones |
| **Tagging** | Auto-tag by heuristics, manual override per add-on, multi-tag support |
| **Bulk actions** | Enable-all / disable-all scoped to the active category |
| **Filtering** | Free-text search across title, description, author, tags, and categories |
| **Status views** | All / Installed / Enabled / Disabled / Available (repository catalog) |
| **Install** | One-click install for extensions available in configured repositories |
| **Persistence** | Categories and tags survive between Blender sessions |
| **Backup** | Export to JSON, import with optional replace-existing mode |
| **Integration** | Adds a button to the Preferences navigation bar; prepends a view-switch to the Add-ons and Extensions panels |

---

## Screenshots

> The bundled ZIP currently contains no screenshots; placeholders describe the layout.

**Category Manager view** — split layout with categories on the left (23% width) and 4-column add-on cards on the right (77%).

**Navigation bar** — the native Blender Preferences nav, with an extra **Categories** shortcut button appended.

**View switcher** — at the top of the Add-ons and Extensions panels, a two-state toggle (**Category Manager** / **Default View**) that does not hide the native UI.

---

## Installation

### From a ZIP file

1. Download `addon_categories.zip`.
2. Open Blender → **Edit → Preferences → Add-ons**.
3. Click **Install from Disk…** (top-right) and pick the ZIP.
4. Enable **Extension & Add-on Categories** in the list.
5. Switch to **Get Extensions** tab too — the add-on hooks both panels.

### From source

```bash
git clone <repo-url>
cd addon_categorias
```

Then in Blender: **Edit → Preferences → Add-ons → Install from Disk…** and select the folder (or zip it first).

### As a Blender Extension (4.2+)

The manifest at `blender_manifest.toml` declares `type = "add-on"` with `schema_version = "1.0.0"`. After signing, the ZIP can be published to the Extensions platform and installed directly from **Get Extensions**.

---

## Quick start

1. Open **Edit → Preferences → Add-ons**. The add-on auto-registers 10 default categories the first time it loads.
3. Click the new **Categories** button in the navigation bar to jump straight into the manager view.
2. Pick a category on the left. The right pane shows every add-on tagged (manually or heuristically) with that label.
4. Use the **Enable All** / **Disable All** buttons in the top-right to flip a whole category at once. The add-on protects itself from being disabled.
5. Click the **+** icon on any card to assign additional categories. The new tag overrides the heuristic for that add-on.
6. Use **Export JSON** to back up your taxonomy.

---

## Default categories

Shipped out of the box:

| ID | Display name | Icon | Used for |
|---|---|---|---|
| `favorites` | Favorites | Solo on | Star / frequently used |
| `modeling` | Modeling | Mesh cube | Mesh edit, hard-surface, modifiers |
| `sculpting` | Sculpting | Sculpt mode | Brushes, multires, voxel remesh |
| `rigging` | Rigging & Armature | Armature | Bones, skinning, IK/FK, mocap |
| `animation` | Animation | Action | Keyframes, NLA, motion tools |
| `render_lighting` | Render & Lighting | Shading rendered | Cycles, Eevee, HDRI |
| `materials_shading` | Materials & Shading | Material | Shaders, nodes, PBR |
| `uv_texturing` | UV & Texturing | UV | Unwrap, layout, pack |
| `import_export` | Import & Export | Import arrow | FBX, glTF, USD, Alembic |
| `pipeline_utils` | Pipeline & Utilities | Preferences | Productivity, UI, system tools |

You can rename built-in categories, add custom ones, or wipe everything with **Reset to Defaults** (also clears all tag assignments).

---

## Auto-tagging heuristic

When an add-on has **no manual tag**, it is auto-classified by a 3-level waterfall (`presets.match_default_categories`):

1. **Legacy `category` field** — exact substring match against the add-on's `bl_info["category"]` (e.g. `"Add Mesh"` → Modeling).
2. **Extension `tags` field** — keyword intersection with the rules in `presets.CATEGORY_RULES`.
3. **Title + description corpus** — same rules, broader text window.

If nothing matches, the add-on lands in **Pipeline & Utilities** as a safe default. This means the bulk enable/disable buttons always have *something* to act on.

The heuristic is conservative: when an add-on matches multiple rules (e.g. a sculpting add-on that also mentions materials), it will receive **multiple tags**, not a single best guess. The card UI shows the first one and a `+N` overflow indicator.

---

## User interface

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ [Search title, author…]              [Status: All ▾]             │  ← top filter row
│ [Enable All (X)] [Disable All (X)]   [Export] [Import] [⋮]        │  ← bulk + tools (kebab hides Reset)
├──────────────────────┬───────────────────────────────────────────┤
│  All Items (NN)      │   <Active Category> — N items found       │
│ ─────                │   ┌─────────────────────────────────────┐ │
│  Favorites (N)       │   │ ✓ │ Title of the add-on    ▣ Sculpt │ │
│  Modeling (N)        │   │   │ Short description…    ▣ Render │ │
│  Sculpting (N)       │   │   │ by Author • v1.2.3    +1 more  │ │
│  …                   │   │   │                       [assign]  │ │
│                      │   └─────────────────────────────────────┘ │
│  [+ Add Category]    │   ┌─────────────────────────────────────┐ │
│                      │   │ … (virtualised — scrolls natively)  │ │
│                      │   └─────────────────────────────────────┘ │
└──────────────────────┴───────────────────────────────────────────┘
```

The right-hand list uses Blender's native `UI_UL_list` virtualisation — only the visible rows are rendered, so scrolling is smooth regardless of how many add-ons match the current filter.

### Card row anatomy

```
┌───────────────────────────────────────────────────────────────┐
│ [✓] │ Title of the add-on                  ▣ Sculpting        │
│     │ Short description goes here…        ▣ Render & Lighting │
│     │ by Author • v1.2.3                   +1 more            │
│     │                                      [assign]            │
└───────────────────────────────────────────────────────────────┘
```

- **Left:** toggle/install action as a single icon button.
- **Middle:** title, description, author, version stacked vertically.
- **Right:** tag chips (clickable — clicking removes the tag), overflow count, and an assign button for the full category manager dialog.

### Status icons

| State | Icon | Action on click |
|---|---|---|
| Installed + enabled | `CHECKBOX_HLT` (depressed) | Disable |
| Installed + disabled | `CHECKBOX_DEHLT` | Enable |
| Remote catalog only | `IMPORT` | Install from repo |
| No tags yet | `BOOKMARKS` ("Add tag…") | — (just a label) |

---

## JSON export / import

The export operator produces this shape:

```json
{
  "version": 1,
  "categories": [
    {
      "name": "Favorites",
      "icon": "SOLO_ON",
      "is_builtin": true,
      "order": 0,
      "description": "Favorite and frequently used add-ons"
    }
  ],
  "assigned_tags": [
    {"addon_id": "io_anim_bvh", "category_name": "Favorites"}
  ]
}
```

- **Export** writes whatever is currently in `AddonPreferences.categories` and `AddonPreferences.assigned_tags`.
- **Import** is additive by default — duplicate category names are skipped, duplicate tags are skipped. Tick **Replace Existing** to clear before importing.
- The `version` field is reserved for future migrations. v1 schemas are forward-compatible.

### Sharing across machines

Export on machine A → drop the file on machine B → **Import JSON** with **Replace Existing** unchecked if you want to merge taxonomies, checked if you want a clean slate.

---

## Operators reference

All operators live in the `addon_categories.*` namespace.

| ID | Purpose | Internal? |
|---|---|---|
| `addon_categories.select_category` | Switch active filter | yes |
| `addon_categories.add_category` | Create custom category (with icon picker) | no |
| `addon_categories.remove_category` | Delete a custom category and its tags | no |
| `addon_categories.rename_category` | Rename a category in place, rewrites tags | no |
| `addon_categories.reset_defaults` | Wipe categories + tags and re-seed defaults | no |
| `addon_categories.reset_tags` | Clear all tag assignments, keep categories | no |
| `addon_categories.reset_custom_categories` | Remove user-defined categories (built-ins kept) | no |
| `addon_categories.toggle_addon` | Enable / disable by module name (refuses remote IDs) | yes |
| `addon_categories.enable_category_all` | Bulk enable within active category | no |
| `addon_categories.disable_category_all` | Bulk disable, **skips itself** | no |
| `addon_categories.toggle_tag` | Flip a single (addon, category) tag from a chip | yes |
| `addon_categories.assign_popup` | Multi-select category dialog per add-on | yes |
| `addon_categories.install_remote` | Install extension from configured repo | no |
| `addon_categories.export_json` | Backup to JSON (ExportHelper file dialog) | no |
| `addon_categories.import_json` | Restore from JSON (ImportHelper file dialog) | no |
| `addon_categories.load_more` | Reset scroll position to top of the list | yes |
| `addon_categories.open_manager` | Jump to Add-ons tab and switch to Category view | yes |

Internal operators (`bl_options = {'INTERNAL'}`) are not exposed in the F3 search menu by design.

---

## Preferences storage

Two `CollectionProperty` slots live on `AddonCategoriesPreferences`:

| Property | Type | Holds |
|---|---|---|
| `categories` | `CategoryItem[]` | Display name, icon, built-in flag, order, description |
| `assigned_tags` | `AddonCategoryTag[]` | (addon_id, category_name) tuples |

Plus scalars:

| Property | Default | Notes |
|---|---|---|
| `active_category` | `"All"` | Current filter on the left sidebar |
| `search_query` | `""` | Free-text filter, sticky across sessions |
| `status_filter` | `"ALL"` | One of `ALL`/`INSTALLED`/`ENABLED`/`DISABLED`/`AVAILABLE` |
| `view_mode` | `"CATEGORIES"` | When `CATEGORIES`, the manager UI is rendered |
| `list_index` | `0` | Selected row index inside the virtualised `UI_UL_list` |

`ensure_default_categories()` is idempotent — it only seeds categories that are missing.

---

## Compatibility

| Blender | Status |
|---|---|
| 4.2 LTS | ✅ Supported (declared minimum) |
| 4.3 | ✅ Expected compatible (uses only stable `bpy.props`, `addon_utils`, `bl_pkg`) |
| 4.0 / 4.1 | ❌ Manifest schema `1.0.0` requires 4.2+; `bl_pkg` API for remote catalogs differs in earlier versions |

Python: tested under the CPython shipped with Blender 4.2 (3.11). No external pip dependencies.

---

## Development

### Repository layout

```
addon_categorias/
├── __init__.py              # Entry point, bl_info, register/unregister
├── blender_manifest.toml    # Extension manifest (Blender 4.2+) + [icon]
├── icon.png                 # 256×256 icon for the Extensions platform
├── properties.py            # PropertyGroups + AddonPreferences
├── presets.py               # DEFAULT_CATEGORIES + match_default_categories()
├── scanner.py               # AddonItemInfo + scan_all_addons() + filter_addons()
├── operators.py             # All bpy.types.Operator subclasses (20 ops)
├── ui.py                    # UIList virtualizada + Panel + drawing + hooks
├── test_addon.py            # Background-mode smoke tests (8 tests)
├── test_pytest.py           # Pytest-compatible suite (27 tests)
├── run_pytest_inline.py     # Standalone pytest runner (no pytest-bpy needed)
├── addon_categories.zip     # Packaged distribution
└── README.md                # This file
```

### Module boundaries

- `presets.py` is **pure data + pure functions** — no `bpy` import, easy to unit-test outside Blender.
- `scanner.py` owns the `AddonItemInfo` dataclass and is the single source of truth for "what add-ons exist".
- `operators.py` is a thin layer over `preferences.toggle_addon_tag` / `scanner.scan_all_addons` — no business logic.
- `ui.py` only draws; never mutates state except through operators.

### Adding a default category

1. Append a tuple to `presets.DEFAULT_CATEGORIES` (5-tuple: `id, name, icon, description, color`).
2. Add a keyword list to `presets.CATEGORY_RULES` if you want auto-tagging.
3. Bump the add-on version in `__init__.py` (`bl_info["version"]`) and `blender_manifest.toml` (`version`).

The `ensure_default_categories()` helper is additive — existing users keep their current categories and only get the new one.

### Reloading during development

Blender's text-editor "Reload Scripts" works out of the box because `__init__.py` already guards against double-import with `if "properties" in locals()`.

---

## Testing

Two complementary suites are shipped:

### `test_addon.py` — script-style smoke tests (8 cases)

```bash
blender --background --python test_addon.py
```

Runs in plain Blender background mode, no pytest required. Exits 0 on success.

### `test_pytest.py` + `run_pytest_inline.py` — comprehensive pytest suite (27 cases)

Covers defaults, CRUD, reorder, scanner, filters, granular reset, filter presets, operators, and JSON export.

Without pytest-bpy (recommended for most environments):

```bash
blender --background --python run_pytest_inline.py
```

With pytest-bpy (optional):

```bash
blender --background -m pytest -- test_pytest.py -xvs
```

The suite covers:

1. Add-on enablement and preference access.
2. Default category seeding.
3. Manual CRUD on categories and tags.
4. `scanner.scan_all_addons()` returning at least one installed item with a non-empty `assigned_categories`.
5. Filter by category, status, and free-text search.
6. The `select_category` and `load_more` operators.
7. JSON round-trip integrity.
8. Clean disable / unregister.
3. Manual CRUD on categories and tags.
4. `scanner.scan_all_addons()` returning at least one installed item with a non-empty `assigned_categories`.
5. Filter by category, status, and free-text search.
6. The `select_category` and `load_more` operators.
7. JSON round-trip integrity.
8. Clean disable / unregister.

Run it with:

```bash
blender --background --python test_addon.py
```

A successful run prints `ALL TESTS PASSED! ADDON IS VERIFIED AND READY.` and exits 0.

---

## Known limitations

- **Scanning the remote catalog** is a no-op if no extension repository is configured in **Get Extensions → Repositories**. The error is silenced by design; the manager still works on installed items.
- **Bulk enable/disable is not transactional.** A failure on add-on N leaves add-ons 1..N-1 in their new state.
- **`max_display_count` resets per session** when the user clicks **Reset Everything** — intentional, the add-on keeps no pagination state since the list is virtualised.
- **The virtualised `UI_UL_list` does not expose a row cap.** Scrolling handles arbitrary item counts natively; the previous `max_display_count = 60` cap was removed.
- **Pagination is 50 per click.** Power users with 1000+ items will click a lot.
- **No icon file in the manifest yet.** Add `[icon]` to `blender_manifest.toml` once a 256×256 icon ships.
- **`test_addon.py` is not pytest-based.** Integrate via `pytest-bpy` if you need CI.

---

## Roadmap

- [ ] Bundled 256×256 icon for the Extensions platform listing.
- [ ] Reorderable categories (drag-and-drop in the sidebar).
- [ ] Saved filter presets ("My Sculpting Setup", "Render-only", …).
- [ ] Optional `pytest-bpy` migration for CI.
- [ ] Color tags in addition to icons.
- [ ] Per-category "auto-disable on file load" hooks.
- [ ] Live search-as-you-type with debounce.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| The **Categories** view shows nothing | No extension repository configured | Add a repo in **Get Extensions → Repositories** and refresh |
| Bulk Disable did nothing | The category is empty (heuristic gave no matches) | Click **Reset to Defaults** and re-scan, or assign tags manually |
| Custom category disappeared after restart | It was actually a built-in and got renamed — renamed built-ins do persist, but only if you saved them | Re-add it as a custom (un-`is_builtin`) category instead |
| JSON import "added 0 categories" | All names already exist (additive mode) | Tick **Replace Existing** in the import dialog |
| `addon_categories.toggle_addon` reports *Add-on not installed* | The card is for a remote catalog item | Click **Install** on the card first |
| The navigation bar button does nothing | You are not in the **Add-ons** tab | The button switches `active_section` automatically; if you are in another Preferences tab, click into Add-ons once and try again |

---

## License

GNU General Public License v3.0 or later — see the `SPDX:GPL-3.0-or-later` declaration in `blender_manifest.toml` and the standard `GPL` header on every Python file.

You are free to use, modify, and redistribute under the same terms. Commercial redistribution is allowed; the source must remain open.

---

## Credits

- **Author** — Yuri
- **Co-pilot** — Antigravity
- **API surface** — Blender Python `bpy`, `addon_utils`, `bl_pkg` (Extensions platform)
- **Built for** — Blender 4.2 LTS and newer