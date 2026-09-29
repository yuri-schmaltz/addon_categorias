"""
Operators for category CRUD, addon bulk toggles, tagging, and JSON export/import.
"""

import json
import os
import addon_utils
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

try:
    from .scanner import get_preferences, scan_all_addons, filter_addons
    from .presets import DEFAULT_CATEGORIES
except (ImportError, ValueError):
    from scanner import get_preferences, scan_all_addons, filter_addons
    from presets import DEFAULT_CATEGORIES


class CATEGORY_OT_select(bpy.types.Operator):
    """Switch active category filter"""
    bl_idname = "addon_categories.select_category"
    bl_label = "Select Category"
    bl_options = {'INTERNAL'}

    category_name: StringProperty(name="Category Name", default="All")

    def execute(self, context):
        prefs = get_preferences(context)
        if prefs:
            prefs.active_category = self.category_name
        return {'FINISHED'}


class CATEGORY_OT_add_category(bpy.types.Operator):
    """Create a new custom category"""
    bl_idname = "addon_categories.add_category"
    bl_label = "Add New Category"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Category Name", default="New Category")
    icon: EnumProperty(
        name="Icon",
        items=[
            ("BOOKMARKS", "Bookmarks", "Bookmark / Tag"),
            ("SOLO_ON", "Favorite", "Star / Favorite"),
            ("MESH_CUBE", "Modeling", "Cube / Mesh"),
            ("SCULPTMODE_HLT", "Sculpting", "Sculpt brush"),
            ("ARMATURE_DATA", "Rigging", "Bone / Armature"),
            ("ACTION", "Animation", "Action / Clapperboard"),
            ("SHADING_RENDERED", "Render & Lighting", "Light / Render"),
            ("MATERIAL", "Materials", "Material sphere"),
            ("UV", "UV", "UV map coordinates"),
            ("IMPORT", "Import & Export", "Import arrow"),
            ("PREFERENCES", "Utilities", "Gear / Preferences"),
            ("COLOR", "Palette", "Artistic / Color"),
            ("FILE_FOLDER", "Folder", "General Folder"),
            ("TOOL_SETTINGS", "Tool", "Wrench tool"),
        ],
        default="BOOKMARKS",
    )
    description: StringProperty(name="Description", default="")
    color: bpy.props.FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=4,
        default=(0.5, 0.5, 0.5, 1.0),
        min=0.0,
        max=1.0,
    )

    def invoke(self, context, event):
        self.name = "New Category"
        self.description = ""
        return context.window_manager.invoke_props_dialog(self, width=340)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "name")
        col.prop(self, "icon")
        col.prop(self, "color")
        col.prop(self, "description")

    def execute(self, context):
        name = self.name.strip()
        if not name:
            self.report({'ERROR'}, "Category name cannot be empty")
            return {'CANCELLED'}

        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        for cat in prefs.categories:
            if cat.name.lower() == name.lower():
                self.report({'WARNING'}, f"Category '{name}' already exists")
                return {'CANCELLED'}

        item = prefs.categories.add()
        item.name = name
        item.icon = self.icon
        item.description = self.description
        item.color = tuple(self.color)
        item.is_builtin = False
        item.order = len(prefs.categories)

        prefs.active_category = name
        self.report({'INFO'}, f"Category '{name}' created")
        return {'FINISHED'}


class CATEGORY_OT_remove_category(bpy.types.Operator):
    """Delete a custom category"""
    bl_idname = "addon_categories.remove_category"
    bl_label = "Remove Category"
    bl_options = {'REGISTER', 'UNDO'}

    category_name: StringProperty(name="Category Name")

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        target_idx = -1
        for idx, cat in enumerate(prefs.categories):
            if cat.name == self.category_name:
                target_idx = idx
                break

        if target_idx >= 0:
            cat_name = prefs.categories[target_idx].name
            prefs.categories.remove(target_idx)
            prefs.remove_category_tags(cat_name)
            if prefs.active_category == cat_name:
                prefs.active_category = "All"
            self.report({'INFO'}, f"Category '{cat_name}' removed")
            return {'FINISHED'}

        self.report({'WARNING'}, "Category not found")
        return {'CANCELLED'}


class CATEGORY_OT_move_category(bpy.types.Operator):
    """Move a category one position up or down in the sidebar."""
    bl_idname = "addon_categories.move_category"
    bl_label = "Reorder Category"
    bl_options = {'INTERNAL'}

    category_name: StringProperty(name="Category Name")
    direction: EnumProperty(
        name="Direction",
        items=[("UP", "Up", ""), ("DOWN", "Down", "")],
        default="UP",
    )

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        target_idx = -1
        for idx, cat in enumerate(prefs.categories):
            if cat.name == self.category_name:
                target_idx = idx
                break
        if target_idx < 0:
            return {'CANCELLED'}

        if self.direction == "UP" and target_idx > 0:
            prefs.categories.move(target_idx, target_idx - 1)
        elif self.direction == "DOWN" and target_idx < len(prefs.categories) - 1:
            prefs.categories.move(target_idx, target_idx + 1)
        else:
            return {'CANCELLED'}

        # Refresh order index on every item so the JSON export reflects it.
        for i, cat in enumerate(prefs.categories):
            cat.order = i

        return {'FINISHED'}


class CATEGORY_OT_rename_category(bpy.types.Operator):
    """Rename a category"""
    bl_idname = "addon_categories.rename_category"
    bl_label = "Rename Category"
    bl_options = {'REGISTER', 'UNDO'}

    old_name: StringProperty(name="Current Name")
    new_name: StringProperty(name="New Name")

    def invoke(self, context, event):
        self.new_name = self.old_name
        return context.window_manager.invoke_props_dialog(self, width=320)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_name")

    def execute(self, context):
        new_name = self.new_name.strip()
        if not new_name or new_name == self.old_name:
            return {'CANCELLED'}

        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        for cat in prefs.categories:
            if cat.name == self.old_name:
                cat.name = new_name
                prefs.rename_category_tags(self.old_name, new_name)
                if prefs.active_category == self.old_name:
                    prefs.active_category = new_name
                self.report({'INFO'}, f"Renamed to '{new_name}'")
                return {'FINISHED'}

        return {'CANCELLED'}


class CATEGORY_OT_reset_defaults(bpy.types.Operator):
    """Reset categories and associations to factory defaults"""
    bl_idname = "addon_categories.reset_defaults"
    bl_label = "Reset Everything to Defaults"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        prefs.categories.clear()
        prefs.assigned_tags.clear()
        prefs.ensure_default_categories()
        prefs.active_category = "All"
        self.report({'INFO'}, "Categories reset to factory defaults")
        return {'FINISHED'}


class CATEGORY_OT_reset_tags(bpy.types.Operator):
    """Reset all manual tag assignments (keeps categories)."""
    bl_idname = "addon_categories.reset_tags"
    bl_label = "Reset Tag Assignments Only"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        removed = len(prefs.assigned_tags)
        prefs.assigned_tags.clear()
        self.report({'INFO'}, f"Cleared {removed} tag assignments (categories kept)")
        return {'FINISHED'}


class CATEGORY_OT_reset_custom_categories(bpy.types.Operator):
    """Remove user-defined categories (built-in ones are kept)."""
    bl_idname = "addon_categories.reset_custom_categories"
    bl_label = "Remove Custom Categories"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        # Collect names first; tags must be wiped before categories (else refs dangle).
        custom_names = [c.name for c in prefs.categories if not c.is_builtin]
        for name in custom_names:
            prefs.remove_category_tags(name)

        # Remove in reverse to keep indices stable.
        for i in reversed(range(len(prefs.categories))):
            if not prefs.categories[i].is_builtin:
                prefs.categories.remove(i)

        if prefs.active_category in custom_names:
            prefs.active_category = "All"

        self.report({'INFO'}, f"Removed {len(custom_names)} custom categories")
        return {'FINISHED'}


class CATEGORY_OT_toggle_addon(bpy.types.Operator):
    """Enable or disable an add-on"""
    bl_idname = "addon_categories.toggle_addon"
    bl_label = "Toggle Add-on"
    bl_options = {'INTERNAL'}

    module_name: StringProperty(name="Module Name")

    def execute(self, context):
        mod_name = self.module_name

        # Defend against remote/catalog IDs that are not yet installed —
        # addon_utils.check() raises ModuleNotFoundError for unknown modules.
        if mod_name.startswith("remote:"):
            self.report({'WARNING'}, "Remote add-ons must be installed first")
            return {'CANCELLED'}

        try:
            is_enabled, _ = addon_utils.check(mod_name)
        except ModuleNotFoundError:
            self.report({'ERROR'}, f"Add-on '{mod_name}' is not installed")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Cannot toggle '{mod_name}': {e}")
            return {'CANCELLED'}

        try:
            if is_enabled:
                addon_utils.disable(mod_name, default_set=True)
                self.report({'INFO'}, f"Disabled '{mod_name}'")
            else:
                addon_utils.enable(mod_name, default_set=True)
                self.report({'INFO'}, f"Enabled '{mod_name}'")
        except Exception as e:
            self.report({'ERROR'}, f"Toggle failed for '{mod_name}': {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


class CATEGORY_OT_enable_category_all(bpy.types.Operator):
    """Enable all installed add-ons in the selected category"""
    bl_idname = "addon_categories.enable_category_all"
    bl_label = "Enable All"
    bl_options = {'REGISTER', 'UNDO'}

    category_name: StringProperty(name="Category Name")

    def execute(self, context):
        items = scan_all_addons(context)
        target_cat = self.category_name
        to_enable = [
            item for item in items
            if item.is_installed and (not target_cat or target_cat == "All" or target_cat in item.assigned_categories)
        ]

        count = 0
        for item in to_enable:
            if not item.is_enabled:
                try:
                    addon_utils.enable(item.id, default_set=True)
                    count += 1
                except Exception as e:
                    print(f"Error enabling {item.id}: {e}")

        self.report({'INFO'}, f"Enabled {count} add-ons in '{target_cat}'")
        return {'FINISHED'}


class CATEGORY_OT_disable_category_all(bpy.types.Operator):
    """Disable all installed add-ons in the selected category"""
    bl_idname = "addon_categories.disable_category_all"
    bl_label = "Disable All"
    bl_options = {'REGISTER', 'UNDO'}

    category_name: StringProperty(name="Category Name")

    def execute(self, context):
        items = scan_all_addons(context)
        target_cat = self.category_name
        # Keep our own addon enabled so the user doesn't turn off this tool
        own_id = __package__ or "addon_categorias"

        to_disable = [
            item for item in items
            if item.is_installed and item.id != own_id and (not target_cat or target_cat == "All" or target_cat in item.assigned_categories)
        ]

        count = 0
        for item in to_disable:
            if item.is_enabled:
                try:
                    addon_utils.disable(item.id, default_set=True)
                    count += 1
                except Exception as e:
                    print(f"Error disabling {item.id}: {e}")

        self.report({'INFO'}, f"Disabled {count} add-ons in '{target_cat}'")
        return {'FINISHED'}


class CATEGORY_OT_toggle_tag(bpy.types.Operator):
    """Assign or unassign a category tag to an add-on"""
    bl_idname = "addon_categories.toggle_tag"
    bl_label = "Toggle Category Tag"
    bl_options = {'INTERNAL'}

    addon_id: StringProperty(name="Add-on ID")
    category_name: StringProperty(name="Category Name")

    def execute(self, context):
        prefs = get_preferences(context)
        if prefs:
            new_state = prefs.toggle_addon_tag(self.addon_id, self.category_name)
            msg = f"Added '{self.category_name}'" if new_state else f"Removed '{self.category_name}'"
            self.report({'INFO'}, msg)
        return {'FINISHED'}


class CATEGORY_OT_assign_popup(bpy.types.Operator):
    """Manage categories assigned to an add-on"""
    bl_idname = "addon_categories.assign_popup"
    bl_label = "Manage Categories"
    bl_options = {'INTERNAL'}

    addon_id: StringProperty(name="Add-on ID")
    addon_title: StringProperty(name="Add-on Title")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=280)

    def draw(self, context):
        layout = self.layout
        prefs = get_preferences(context)
        if not prefs:
            return

        layout.label(text=f"Add-on: {self.addon_title}", icon='SCRIPT')
        layout.separator()

        col = layout.column(align=True)
        assigned = prefs.get_addon_categories(self.addon_id)

        for cat in prefs.categories:
            is_assigned = cat.name in assigned
            row = col.row(align=True)
            icon = 'CHECKBOX_HLT' if is_assigned else 'CHECKBOX_DEHLT'
            op = row.operator("addon_categories.toggle_tag", text=cat.name, icon=icon)
            op.addon_id = self.addon_id
            op.category_name = cat.name

    def execute(self, context):
        return {'FINISHED'}


class CATEGORY_OT_install_remote(bpy.types.Operator):
    """Install an extension from repository"""
    bl_idname = "addon_categories.install_remote"
    bl_label = "Install Extension"
    bl_options = {'REGISTER'}

    pkg_id: StringProperty(name="Package ID")
    repo_directory: StringProperty(name="Repo Directory")

    def execute(self, context):
        clean_id = self.pkg_id.replace("remote:", "")
        try:
            bpy.ops.extensions.package_install(
                repo_directory=self.repo_directory,
                pkg_id=clean_id,
                enable_on_install=True,
            )
            self.report({'INFO'}, f"Installed '{clean_id}'")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Install failed: {e}")
            return {'CANCELLED'}


class CATEGORY_OT_export_json(bpy.types.Operator, ExportHelper):
    """Export custom categories and assigned tags to a JSON file"""
    bl_idname = "addon_categories.export_json"
    bl_label = "Export Categories (JSON)"
    bl_options = {'REGISTER'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        data = {
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

        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.report({'INFO'}, f"Exported {len(data['categories'])} categories to {os.path.basename(self.filepath)}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}


class CATEGORY_OT_import_json(bpy.types.Operator, ImportHelper):
    """Import categories and tags from a JSON backup file"""
    bl_idname = "addon_categories.import_json"
    bl_label = "Import Categories (JSON)"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    replace_existing: BoolProperty(
        name="Replace Existing",
        description="Clear current categories before importing",
        default=False,
    )

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            raw_categories = data.get("categories", [])
            raw_tags = data.get("assigned_tags", [])

            if self.replace_existing:
                prefs.categories.clear()
                prefs.assigned_tags.clear()

            existing_cat_names = {c.name for c in prefs.categories}
            for cat_dict in raw_categories:
                name = cat_dict.get("name", "").strip()
                if name and name not in existing_cat_names:
                    item = prefs.categories.add()
                    item.name = name
                    item.icon = cat_dict.get("icon", "BOOKMARKS")
                    item.is_builtin = cat_dict.get("is_builtin", False)
                    item.order = cat_dict.get("order", len(prefs.categories))
                    item.description = cat_dict.get("description", "")
                    existing_cat_names.add(name)

            for tag_dict in raw_tags:
                addon_id = tag_dict.get("addon_id", "")
                cat_name = tag_dict.get("category_name", "")
                if addon_id and cat_name and not prefs.has_tag(addon_id, cat_name):
                    t = prefs.assigned_tags.add()
                    t.addon_id = addon_id
                    t.category_name = cat_name

            self.report({'INFO'}, f"Imported {len(raw_categories)} categories successfully")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}


class CATEGORY_OT_load_more(bpy.types.Operator):
    """Reset list selection to the top (no-op with virtualised list)."""
    bl_idname = "addon_categories.load_more"
    bl_label = "Scroll to Top"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        prefs = get_preferences(context)
        if prefs:
            prefs.list_index = 0
        return {'FINISHED'}


class CATEGORY_OT_save_filter_preset(bpy.types.Operator):
    """Save the current filter state (category + search + status) as a named preset."""
    bl_idname = "addon_categories.save_filter_preset"
    bl_label = "Save Filter Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset_name: StringProperty(name="Preset Name", default="My Setup")

    def invoke(self, context, event):
        self.preset_name = "My Setup"
        return context.window_manager.invoke_props_dialog(self, width=280)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Snapshot the current filter state:", icon='BOOKMARKS')
        layout.prop(self, "preset_name")

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        name = self.preset_name.strip()
        if not name:
            self.report({'ERROR'}, "Preset name cannot be empty")
            return {'CANCELLED'}

        # Replace existing preset with the same name (idempotent save).
        for i, existing in enumerate(prefs.filter_presets):
            if existing.name == name:
                prefs.filter_presets.remove(i)
                break

        preset = prefs.filter_presets.add()
        preset.name = name
        preset.category = prefs.active_category or "All"
        preset.search_query = prefs.search_query or ""
        preset.status_filter = prefs.status_filter or "ALL"
        # Use a simple timestamp marker — not parsed, just a hint of recency.
        preset.created_at = ""

        self.report({'INFO'}, f"Preset '{name}' saved")
        return {'FINISHED'}


class CATEGORY_OT_apply_filter_preset(bpy.types.Operator):
    """Restore the filter state stored in a preset."""
    bl_idname = "addon_categories.apply_filter_preset"
    bl_label = "Apply Filter Preset"
    bl_options = {'INTERNAL'}

    preset_name: StringProperty(name="Preset Name")

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        for preset in prefs.filter_presets:
            if preset.name == self.preset_name:
                prefs.active_category = preset.category
                prefs.search_query = preset.search_query
                prefs.status_filter = preset.status_filter
                prefs.list_index = 0
                self.report({'INFO'}, f"Applied preset '{self.preset_name}'")
                return {'FINISHED'}

        self.report({'WARNING'}, f"Preset '{self.preset_name}' not found")
        return {'CANCELLED'}


class CATEGORY_OT_remove_filter_preset(bpy.types.Operator):
    """Delete a saved filter preset."""
    bl_idname = "addon_categories.remove_filter_preset"
    bl_label = "Remove Filter Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset_name: StringProperty(name="Preset Name")

    def execute(self, context):
        prefs = get_preferences(context)
        if not prefs:
            return {'CANCELLED'}

        for i, preset in enumerate(prefs.filter_presets):
            if preset.name == self.preset_name:
                prefs.filter_presets.remove(i)
                self.report({'INFO'}, f"Preset '{self.preset_name}' removed")
                return {'FINISHED'}

        return {'CANCELLED'}


classes = (
    CATEGORY_OT_select,
    CATEGORY_OT_add_category,
    CATEGORY_OT_remove_category,
    CATEGORY_OT_move_category,
    CATEGORY_OT_rename_category,
    CATEGORY_OT_reset_defaults,
    CATEGORY_OT_reset_tags,
    CATEGORY_OT_reset_custom_categories,
    CATEGORY_OT_toggle_addon,
    CATEGORY_OT_enable_category_all,
    CATEGORY_OT_disable_category_all,
    CATEGORY_OT_toggle_tag,
    CATEGORY_OT_assign_popup,
    CATEGORY_OT_install_remote,
    CATEGORY_OT_export_json,
    CATEGORY_OT_import_json,
    CATEGORY_OT_load_more,
    CATEGORY_OT_save_filter_preset,
    CATEGORY_OT_apply_filter_preset,
    CATEGORY_OT_remove_filter_preset,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            # Class already unregistered or not yet registered — safe to ignore.
            pass
