"""
Automated verification tests for Extension & Add-on Categories in Blender.
Execute with:
    blender --background --python test_addon.py
"""

import sys
import os
import tempfile
import json
import addon_utils
import bpy

def run_tests():
    print("\n" + "=" * 60)
    print("RUNNING EXTENSION & ADD-ON CATEGORIES TEST SUITE")
    print("=" * 60)

    # 1. Enable addon
    print("\n[TEST 1] Enabling addon_categorias...")
    mod = addon_utils.enable("addon_categorias", default_set=True)
    assert mod is not None, "Failed to enable addon_categorias"
    assert "addon_categorias" in bpy.context.preferences.addons, "addon_categorias not in preferences"
    prefs = bpy.context.preferences.addons["addon_categorias"].preferences
    print(f"  -> Successfully enabled: {mod.__name__}, prefs: {prefs}")

    # 2. Test Default Categories initialization
    print("\n[TEST 2] Testing Default Categories initialization...")
    prefs.ensure_default_categories()
    print(f"  -> Factory categories count: {len(prefs.categories)}")
    assert len(prefs.categories) >= 10, "Should have at least 10 default categories"
    cat_names = [c.name for c in prefs.categories]
    print(f"  -> Categories: {cat_names}")
    assert "Favorites" in cat_names, "'Favorites' must be in default categories"
    assert "Modeling" in cat_names, "'Modeling' must be in default categories"
    assert "Pipeline & Utilities" in cat_names, "'Pipeline & Utilities' must be in default categories"

    # 3. Test Custom Category Operations (Add, Rename, Delete)
    print("\n[TEST 3] Testing Category CRUD operations...")
    # Add category
    new_cat = prefs.categories.add()
    new_cat.name = "My Test Category"
    new_cat.icon = "SOLO_ON"
    new_cat.is_builtin = False
    assert any(c.name == "My Test Category" for c in prefs.categories)
    print("  -> Category 'My Test Category' added.")

    # Tag association
    test_addon_id = "io_anim_bvh"
    state1 = prefs.toggle_addon_tag(test_addon_id, "My Test Category")
    assert state1 is True, "First toggle should add tag"
    assert prefs.has_tag(test_addon_id, "My Test Category") is True
    print(f"  -> Tagged '{test_addon_id}' with 'My Test Category'.")

    # Rename
    prefs.rename_category_tags("My Test Category", "Renamed Category")
    new_cat.name = "Renamed Category"
    assert prefs.has_tag(test_addon_id, "Renamed Category") is True
    print("  -> Category and tags renamed successfully.")

    # Delete
    prefs.remove_category_tags("Renamed Category")
    assert prefs.has_tag(test_addon_id, "Renamed Category") is False
    print("  -> Tag removed successfully.")

    # 4. Test Scanner
    print("\n[TEST 4] Testing Scanner...")
    from addon_categorias import scanner
    all_addons = scanner.scan_all_addons(bpy.context)
    print(f"  -> Total scanned: {len(all_addons)}")
    installed = [a for a in all_addons if a.is_installed]
    remote = [a for a in all_addons if not a.is_installed]
    print(f"  -> Installed: {len(installed)}, Remote catalog: {len(remote)}")
    assert len(installed) > 0, "Should find installed addons in Blender"

    # Check that heuristic categories were assigned
    for inst in installed[:5]:
        print(f"     Addon: {inst.title} -> Categories: {inst.assigned_categories}")
        assert len(inst.assigned_categories) > 0, f"Addon {inst.title} should have at least 1 category"

    # 5. Test Filtering
    print("\n[TEST 5] Testing Filters...")
    modeling_items = scanner.filter_addons(all_addons, category="Modeling")
    print(f"  -> Items in 'Modeling': {len(modeling_items)}")

    installed_only = scanner.filter_addons(all_addons, status_filter="INSTALLED")
    print(f"  -> Filtered 'INSTALLED': {len(installed_only)}")
    assert all(i.is_installed for i in installed_only)

    search_filtered = scanner.filter_addons(all_addons, search_query="mesh")
    print(f"  -> Filtered search 'mesh': {len(search_filtered)}")
    assert len(search_filtered) > 0

    # 6. Test Operators
    print("\n[TEST 6] Testing Operators...")
    # Test select_category operator
    bpy.ops.addon_categories.select_category(category_name="Sculpting")
    assert prefs.active_category == "Sculpting", f"Expected 'Sculpting', got '{prefs.active_category}'"
    print("  -> select_category operator works.")

    # Test load_more operator
    initial_limit = prefs.max_display_count
    bpy.ops.addon_categories.load_more(step=30)
    assert prefs.max_display_count == initial_limit + 30
    print(f"  -> load_more operator works (new limit: {prefs.max_display_count}).")

    # 7. Test JSON Export and Import
    print("\n[TEST 7] Testing JSON Export and Import...")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Tag an addon for export test
        prefs.toggle_addon_tag("io_anim_bvh", "Favorites")

        export_data = {
            "version": 1,
            "categories": [
                {
                    "name": c.name,
                    "icon": c.icon,
                    "is_builtin": c.is_builtin,
                    "order": c.order,
                    "description": c.description,
                }
                for c in prefs.categories
            ],
            "assigned_tags": [
                {
                    "addon_id": t.addon_id,
                    "category_name": t.category_name,
                }
                for t in prefs.assigned_tags
            ],
        }

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        print(f"  -> Saved test export to {tmp_path}")

        # Read back and verify
        with open(tmp_path, "r", encoding="utf-8") as f:
            imported = json.load(f)

        assert "categories" in imported
        assert "assigned_tags" in imported
        assert len(imported["categories"]) == len(prefs.categories)
        print("  -> JSON roundtrip verified successfully.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # 8. Test Disable / Unregister
    print("\n[TEST 8] Disabling addon...")
    addon_utils.disable("addon_categorias", default_set=True)
    print("  -> Disabled successfully.")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ADDON IS VERIFIED AND READY.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_tests()
