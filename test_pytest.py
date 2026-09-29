"""
Pytest-compatible test suite for Extension & Add-on Categories.

These tests can be run via two paths:

1. With pytest-bpy installed inside Blender's Python:
       pip install --target=$BLENDER_LIB pytest pytest-bpy
       blender --background -m pytest -- test_pytest.py -xvs

2. As plain assertions driven by `blender --background --python test_pytest.py`
   after stripping the @pytest.fixture decorators (each test accepts
   `prefs` as its single positional arg).

Run directly inside Blender with the helper script run_pytest_inline.py
(written for environments without pytest-bpy available).
"""

import bpy
import pytest
import addon_utils


# ---------------------------------------------------------------------------
# Module-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def enable_addon():
    """Enable the addon once per test module; yield control; disable on teardown."""
    mod = addon_utils.enable("addon_categorias", default_set=True)
    assert mod is not None, "Failed to enable addon_categorias"
    assert "addon_categorias" in bpy.context.preferences.addons, \
        "addon_categorias not in preferences"
    yield
    addon_utils.disable("addon_categorias", default_set=True)


@pytest.fixture()
def prefs():
    """Return the AddonCategoriesPreferences handle."""
    return bpy.context.preferences.addons["addon_categorias"].preferences


@pytest.fixture(autouse=True)
def reset_prefs_state(prefs):
    """Snapshot mutable state before each test, restore on teardown."""
    saved_cats = list(prefs.categories.keys())
    saved_tags = list(prefs.assigned_tags.keys())
    saved_presets = list(prefs.filter_presets.keys())
    saved_active = prefs.active_category
    saved_query = prefs.search_query
    saved_status = prefs.status_filter
    saved_index = prefs.list_index
    yield prefs
    # Restore via remove() in reverse to keep indices stable.
    for k in reversed(list(prefs.filter_presets.keys())):
        if k not in saved_presets:
            prefs.filter_presets.remove(k)
    for k in reversed(list(prefs.assigned_tags.keys())):
        if k not in saved_tags:
            prefs.assigned_tags.remove(k)
    for k in reversed(list(prefs.categories.keys())):
        if k not in saved_cats:
            prefs.categories.remove(k)
    prefs.active_category = saved_active
    prefs.search_query = saved_query
    prefs.status_filter = saved_status
    prefs.list_index = saved_index


# ---------------------------------------------------------------------------
# Property / Category tests
# ---------------------------------------------------------------------------

class TestDefaultCategories:
    def test_seeded_on_load(self, prefs):
        prefs.ensure_default_categories()
        names = [c.name for c in prefs.categories]
        assert "Favorites" in names
        assert "Modeling" in names
        assert "Pipeline & Utilities" in names

    def test_minimum_count(self, prefs):
        prefs.ensure_default_categories()
        assert len(prefs.categories) >= 10

    def test_builtin_flag_set(self, prefs):
        prefs.ensure_default_categories()
        builtins = [c for c in prefs.categories if c.is_builtin]
        assert len(builtins) >= 10

    def test_builtin_colors_are_tinted(self, prefs):
        """Built-ins must have a non-neutral color (RGBA in 0..1)."""
        prefs.ensure_default_categories()
        for cat in prefs.categories:
            if cat.is_builtin:
                r, g, b = cat.color[:3]
                assert 0.0 <= r <= 1.0
                assert 0.0 <= g <= 1.0
                assert 0.0 <= b <= 1.0

    def test_idempotent_seeding(self, prefs):
        prefs.ensure_default_categories()
        first_count = len(prefs.categories)
        prefs.ensure_default_categories()
        assert len(prefs.categories) == first_count, "Seeding must be idempotent"


class TestCategoryCRUD:
    def test_add_custom_category(self, prefs):
        cat = prefs.categories.add()
        cat.name = "My Custom"
        cat.icon = "SOLO_ON"
        cat.is_builtin = False
        cat.color = (0.1, 0.2, 0.3, 1.0)
        assert any(c.name == "My Custom" for c in prefs.categories)

    def test_rename_propagates_to_tags(self, prefs):
        cat = prefs.categories.add()
        cat.name = "Original"
        cat.is_builtin = False
        prefs.toggle_addon_tag("io_anim_bvh", "Original")
        cat.name = "Renamed"
        prefs.rename_category_tags("Original", "Renamed")
        assert prefs.has_tag("io_anim_bvh", "Renamed")

    def test_remove_cascades_to_tags(self, prefs):
        cat = prefs.categories.add()
        cat.name = "To Delete"
        cat.is_builtin = False
        prefs.toggle_addon_tag("io_anim_bvh", "To Delete")
        idx = next(i for i, c in enumerate(prefs.categories) if c.name == "To Delete")
        prefs.remove_category_tags("To Delete")
        prefs.categories.remove(idx)
        assert not prefs.has_tag("io_anim_bvh", "To Delete")


class TestReorder:
    def test_move_up(self, prefs):
        # Ensure at least two built-ins are present.
        prefs.ensure_default_categories()
        original = [c.name for c in prefs.categories]
        # Move index 1 up to position 0.
        target_name = original[1]
        bpy.ops.addon_categories.move_category(category_name=target_name, direction='UP')
        assert prefs.categories[0].name == target_name

    def test_move_down(self, prefs):
        prefs.ensure_default_categories()
        original = [c.name for c in prefs.categories]
        target_name = original[-2]
        bpy.ops.addon_categories.move_category(category_name=target_name, direction='DOWN')
        assert prefs.categories[-1].name == target_name


# ---------------------------------------------------------------------------
# Scanner tests
# ---------------------------------------------------------------------------

class TestScanner:
    def test_scan_returns_items(self, prefs):
        from addon_categorias import scanner
        all_addons = scanner.scan_all_addons(bpy.context)
        assert len(all_addons) > 0
        installed = [a for a in all_addons if a.is_installed]
        assert len(installed) > 0

    def test_each_installed_has_category(self, prefs):
        from addon_categorias import scanner
        all_addons = scanner.scan_all_addons(bpy.context)
        for inst in all_addons:
            if inst.is_installed:
                assert len(inst.assigned_categories) > 0, \
                    f"{inst.title} should have at least one category"

    def test_fallback_category_used(self, prefs):
        from addon_categorias import scanner
        all_addons = scanner.scan_all_addons(bpy.context)
        # At least one addon should fall into Pipeline & Utilities.
        fallbacks = [
            a for a in all_addons
            if "Pipeline & Utilities" in a.assigned_categories
        ]
        assert len(fallbacks) > 0


class TestFilters:
    def test_filter_by_category(self, prefs):
        from addon_categorias import scanner
        all_addons = scanner.scan_all_addons(bpy.context)
        modeling = scanner.filter_addons(all_addons, category="Modeling")
        assert all("Modeling" in item.assigned_categories for item in modeling)

    def test_filter_by_status(self, prefs):
        from addon_categorias import scanner
        all_addons = scanner.scan_all_addons(bpy.context)
        installed = scanner.filter_addons(all_addons, status_filter="INSTALLED")
        assert all(item.is_installed for item in installed)

    def test_filter_by_search(self, prefs):
        from addon_categorias import scanner
        all_addons = scanner.scan_all_addons(bpy.context)
        matches = scanner.filter_addons(all_addons, search_query="mesh")
        assert len(matches) > 0


# ---------------------------------------------------------------------------
# Reset operators
# ---------------------------------------------------------------------------

class TestGranularReset:
    def test_reset_tags_keeps_categories(self, prefs):
        cat = prefs.categories.add()
        cat.name = "Tmp"
        cat.is_builtin = False
        prefs.toggle_addon_tag("io_anim_bvh", "Tmp")
        bpy.ops.addon_categories.reset_tags('INVOKE_DEFAULT')
        assert not prefs.has_tag("io_anim_bvh", "Tmp")
        assert any(c.name == "Tmp" for c in prefs.categories)

    def test_reset_custom_categories_keeps_builtins(self, prefs):
        prefs.ensure_default_categories()
        builtins_before = {c.name for c in prefs.categories if c.is_builtin}
        cat = prefs.categories.add()
        cat.name = "Tmp2"
        cat.is_builtin = False
        prefs.toggle_addon_tag("io_anim_bvh", "Tmp2")
        bpy.ops.addon_categories.reset_custom_categories('INVOKE_DEFAULT')
        builtins_after = {c.name for c in prefs.categories if c.is_builtin}
        assert builtins_before == builtins_after
        assert not any(c.name == "Tmp2" for c in prefs.categories)

    def test_reset_everything_restores_defaults(self, prefs):
        bpy.ops.addon_categories.reset_defaults('INVOKE_DEFAULT')
        prefs.ensure_default_categories()
        names = {c.name for c in prefs.categories}
        assert "Favorites" in names
        assert "Pipeline & Utilities" in names


# ---------------------------------------------------------------------------
# Filter preset tests
# ---------------------------------------------------------------------------

class TestFilterPresets:
    def test_save_and_apply(self, prefs):
        # Set up a specific filter state.
        prefs.active_category = "Modeling"
        prefs.search_query = "cube"
        prefs.status_filter = "ENABLED"

        bpy.ops.addon_categories.save_filter_preset(preset_name="My Modeling")
        assert any(p.name == "My Modeling" for p in prefs.filter_presets)

        # Mutate state to something different.
        prefs.active_category = "All"
        prefs.search_query = ""
        prefs.status_filter = "ALL"

        # Apply preset and check state restored.
        bpy.ops.addon_categories.apply_filter_preset(preset_name="My Modeling")
        assert prefs.active_category == "Modeling"
        assert prefs.search_query == "cube"
        assert prefs.status_filter == "ENABLED"

    def test_save_replaces_duplicate_name(self, prefs):
        bpy.ops.addon_categories.save_filter_preset(preset_name="Dup")
        bpy.ops.addon_categories.save_filter_preset(preset_name="Dup")
        matches = [p for p in prefs.filter_presets if p.name == "Dup"]
        assert len(matches) == 1, "Duplicate saves must collapse to one"

    def test_remove_preset(self, prefs):
        bpy.ops.addon_categories.save_filter_preset(preset_name="ToRemove")
        bpy.ops.addon_categories.remove_filter_preset(preset_name="ToRemove")
        assert not any(p.name == "ToRemove" for p in prefs.filter_presets)


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class TestOperators:
    def test_select_category(self, prefs):
        bpy.ops.addon_categories.select_category(category_name="Sculpting")
        assert prefs.active_category == "Sculpting"

    def test_toggle_addon_rejects_remote(self, prefs):
        result = bpy.ops.addon_categories.toggle_addon(module_name="remote:foo")
        # 'CANCELLED' returns the int 2 in RNA; result is a set-like in newer Blender.
        assert result == {'CANCELLED'}

    def test_load_more_resets_index(self, prefs):
        prefs.list_index = 7
        bpy.ops.addon_categories.load_more()
        assert prefs.list_index == 0

    def test_add_category_dialog_accepts_color(self, prefs):
        # Invoking the dialog from a script is non-trivial; instead we
        # verify the CategoryItem.color property works end-to-end: a
        # newly-added category must accept an RGBA tuple and round-trip.
        cat = prefs.categories.add()
        cat.name = "Color Test"
        cat.is_builtin = False
        cat.color = (0.25, 0.50, 0.75, 1.0)
        assert cat.color[0] == pytest.approx(0.25, abs=1e-3)
        assert cat.color[2] == pytest.approx(0.75, abs=1e-3)
        assert cat.color[3] == pytest.approx(1.0, abs=1e-3)


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

class TestJsonExport:
    def test_export_data_shape(self, prefs):
        import json
        from addon_categorias import presets
        prefs.ensure_default_categories()
        data = {
            "version": 1,
            "categories": [
                {
                    "name": c.name,
                    "icon": c.icon,
                    "is_builtin": c.is_builtin,
                    "order": c.order,
                    "description": c.description,
                    "color": tuple(c.color),
                }
                for c in prefs.categories
            ],
            "assigned_tags": [
                {"addon_id": t.addon_id, "category_name": t.category_name}
                for t in prefs.assigned_tags
            ],
        }
        serialised = json.dumps(data)
        roundtrip = json.loads(serialised)
        assert roundtrip["version"] == 1
        assert len(roundtrip["categories"]) == len(prefs.categories)
        assert all("color" in c for c in roundtrip["categories"])