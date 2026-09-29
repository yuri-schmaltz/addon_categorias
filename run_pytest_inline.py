"""
Inline pytest runner — invokes all test classes defined in test_pytest.py
inside Blender's Python, without requiring pytest-bpy to be installed.

Usage:
    blender --background --python run_pytest_inline.py
"""

import sys
import os
import bpy
import addon_utils


def main() -> int:
    # Add repo root + any external site-packages to the path.
    repo_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, repo_root)

    # Handle both legacy (addon_categorias) and extension-installed
    # (bl_ext.user_default.addon_categories) module names.
    mod = None
    addon_module_name = None
    for candidate in ("addon_categorias", "bl_ext.user_default.addon_categories"):
        try:
            mod = addon_utils.enable(candidate, default_set=True)
            if mod is not None:
                addon_module_name = candidate
                break
        except Exception:
            continue
    if mod is None:
        print("ERROR: Failed to enable addon_categorias")
        return 2

    prefs_key = None
    for k in bpy.context.preferences.addons.keys():
        entry = bpy.context.preferences.addons[k]
        if entry.preferences is not None and k.endswith("addon_categories"):
            prefs_key = k
            break
    if prefs_key is None:
        print("ERROR: addon_categorias not in preferences")
        return 2

    try:
        import test_pytest
    except ImportError as e:
        print(f"ERROR: cannot import test_pytest: {e}")
        return 2

    prefs = bpy.context.preferences.addons[prefs_key].preferences

    test_classes = [
        getattr(test_pytest, name) for name in [
            "TestDefaultCategories",
            "TestCategoryCRUD",
            "TestReorder",
            "TestScanner",
            "TestFilters",
            "TestGranularReset",
            "TestFilterPresets",
            "TestOperators",
            "TestJsonExport",
        ] if hasattr(test_pytest, name)
    ]

    def snapshot():
        return {
            "cat_count": len(prefs.categories),
            "tag_count": len(prefs.assigned_tags),
            "preset_count": len(prefs.filter_presets),
            "active": prefs.active_category,
            "query": prefs.search_query,
            "status": prefs.status_filter,
            "index": prefs.list_index,
        }

    def restore(snap):
        while len(prefs.filter_presets) > snap["preset_count"]:
            prefs.filter_presets.remove(len(prefs.filter_presets) - 1)
        while len(prefs.assigned_tags) > snap["tag_count"]:
            prefs.assigned_tags.remove(len(prefs.assigned_tags) - 1)
        while len(prefs.categories) > snap["cat_count"]:
            prefs.categories.remove(len(prefs.categories) - 1)
        prefs.active_category = snap["active"]
        prefs.search_query = snap["query"]
        prefs.status_filter = snap["status"]
        prefs.list_index = snap["index"]

    passed = 0
    failed = 0
    errors = []

    print()
    print("=" * 60)
    print("RUNNING PYTEST INLINE SUITE")
    print("=" * 60)

    for cls in test_classes:
        instance = cls()
        for method_name in [m for m in dir(instance) if m.startswith("test_")]:
            snap = snapshot()
            try:
                getattr(instance, method_name)(prefs)
                passed += 1
                print(f"  PASS: {cls.__name__}.{method_name}")
            except AssertionError as e:
                failed += 1
                errors.append((cls.__name__, method_name, str(e)))
                print(f"  FAIL: {cls.__name__}.{method_name} -- {e}")
            except Exception as e:
                failed += 1
                errors.append((cls.__name__, method_name, repr(e)))
                print(f"  ERROR: {cls.__name__}.{method_name} -- {e!r}")
            finally:
                restore(snap)

    print()
    print("=" * 60)
    print(f"TOTAL: {passed + failed} | PASS: {passed} | FAIL: {failed}")
    print("=" * 60)
    if failed:
        print("Failures:")
        for cls_name, method, err in errors:
            print(f"  {cls_name}.{method}: {err}")

    return 0 if failed == 0 else 1


def _cleanup():
    """Disable whichever addon variant was enabled."""
    for candidate in ("addon_categorias", "bl_ext.user_default.addon_categories"):
        try:
            addon_utils.disable(candidate, default_set=True)
        except Exception:
            pass


if __name__ == "__main__":
    rc = main()
    _cleanup()
    sys.exit(rc)