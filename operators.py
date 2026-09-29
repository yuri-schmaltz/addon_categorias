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

    def invoke(self, context, event):
        self.name = "New Category"
        self.description = ""
        return context.window_manager.invoke_props_dialog(self, width=320)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "name")
        col.prop(self, "icon")
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
    bl_label = "Reset to Default Categories"
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


class CATEGORY_OT_toggle_addon(bpy.types.Operator):
    """Enable or disable an add-on"""
    bl_idname = "addon_categories.toggle_addon"
    bl_label = "Toggle Add-on"
    bl_options = {'INTERNAL'}

    module_name: StringProperty(name="Module Name")

    def execute(self, context):
        mod_name = self.module_name
        is_enabled, _ = addon_utils.check(mod_name)
        if is_enabled:
            addon_utils.disable(mod_name, default_set=True)
            self.report({'INFO'}, f"Disabled '{mod_name}'")
        else:
            addon_utils.enable(mod_name, default_set=True)
            self.report({'INFO'}, f"Enabled '{mod_name}'")
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
    """Load more items in the category view"""
    bl_idname = "addon_categories.load_more"
    bl_label = "Load More"
    bl_options = {'INTERNAL'}

    step: bpy.props.IntProperty(default=50)

    def execute(self, context):
        prefs = get_preferences(context)
        if prefs:
            prefs.max_display_count += self.step
        return {'FINISHED'}


classes = (
    CATEGORY_OT_select,
    CATEGORY_OT_add_category,
    CATEGORY_OT_remove_category,
    CATEGORY_OT_rename_category,
    CATEGORY_OT_reset_defaults,
    CATEGORY_OT_toggle_addon,
    CATEGORY_OT_enable_category_all,
    CATEGORY_OT_disable_category_all,
    CATEGORY_OT_toggle_tag,
    CATEGORY_OT_assign_popup,
    CATEGORY_OT_install_remote,
    CATEGORY_OT_export_json,
    CATEGORY_OT_import_json,
    CATEGORY_OT_load_more,
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
        except Exception:
            pass
