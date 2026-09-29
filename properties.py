"""
Data models and preferences properties for Add-on and Extension Categories.
"""

import bpy
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    EnumProperty,
    FloatVectorProperty,
    CollectionProperty,
)
try:
    from .presets import DEFAULT_CATEGORIES
except (ImportError, ValueError):
    from presets import DEFAULT_CATEGORIES



class CategoryItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", default="New Category")
    icon: StringProperty(name="Icon", default="BOOKMARKS")
    is_builtin: BoolProperty(name="Built-in", default=False)
    order: IntProperty(name="Order", default=0)
    description: StringProperty(name="Description", default="")
    # Per-category accent color (RGBA, 0..1). White default so built-ins
    # that lack an explicit color render neutral.
    color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=4,
        default=(1.0, 1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
    )


class AddonCategoryTag(bpy.types.PropertyGroup):
    addon_id: StringProperty(name="Add-on ID", default="")
    category_name: StringProperty(name="Category Name", default="")


class FilterPreset(bpy.types.PropertyGroup):
    """User-saved bundle of filter state (category + search + status)."""
    name: StringProperty(name="Preset Name", default="Untitled Preset")
    category: StringProperty(name="Category", default="All")
    search_query: StringProperty(name="Search", default="")
    status_filter: StringProperty(name="Status", default="ALL")
    created_at: StringProperty(name="Created", default="")


class AddonCategoriesPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__ or "addon_categorias"

    categories: CollectionProperty(type=CategoryItem)
    assigned_tags: CollectionProperty(type=AddonCategoryTag)
    filter_presets: CollectionProperty(type=FilterPreset)

    active_category: StringProperty(name="Active Category", default="All")
    search_query: StringProperty(name="Search", description="Filter add-ons by name or keywords", default="")

    status_filter: EnumProperty(
        name="Status Filter",
        items=[
            ("ALL", "All", "Show all add-ons and extensions"),
            ("INSTALLED", "Installed", "Show installed add-ons and extensions"),
            ("ENABLED", "Enabled", "Show only enabled add-ons"),
            ("DISABLED", "Disabled", "Show disabled add-ons"),
            ("AVAILABLE", "Available", "Show extensions available in repositories"),
        ],
        default="ALL",
    )

    view_mode: EnumProperty(
        name="View Mode",
        items=[
            ("CATEGORIES", "Category Manager", "Show categorized add-on explorer"),
            ("DEFAULT", "Default View", "Show standard list"),
        ],
        default="CATEGORIES",
    )

    list_index: IntProperty(
        name="Selected Item Index",
        description="Index of the currently selected item in the virtualised list",
        default=0,
        min=0,
    )

    def ensure_default_categories(self):
        """Populate default categories if not already present."""
        existing_names = {c.name for c in self.categories}
        for entry in DEFAULT_CATEGORIES:
            # Built-in entries are 5-tuples (id, name, icon, desc, color).
            # Older serialized data on disk may have been written with the
            # 4-tuple format — gracefully fall back to neutral color.
            if len(entry) == 5:
                cid, name, icon, desc, color = entry
            else:
                cid, name, icon, desc = entry[:4]
                color = (1.0, 1.0, 1.0, 1.0)
            if name not in existing_names:
                item = self.categories.add()
                item.name = name
                item.icon = icon
                item.is_builtin = True
                item.order = len(self.categories)
                item.description = desc
                item.color = color

    def get_addon_categories(self, addon_id: str) -> list[str]:
        """Returns all category names assigned to an add-on ID."""
        return [tag.category_name for tag in self.assigned_tags if tag.addon_id == addon_id]

    def has_tag(self, addon_id: str, category_name: str) -> bool:
        """Check if an addon has a specific category tag."""
        for tag in self.assigned_tags:
            if tag.addon_id == addon_id and tag.category_name == category_name:
                return True
        return False

    def toggle_addon_tag(self, addon_id: str, category_name: str) -> bool:
        """Add tag if missing, remove if present. Returns new state."""
        for idx, tag in enumerate(self.assigned_tags):
            if tag.addon_id == addon_id and tag.category_name == category_name:
                self.assigned_tags.remove(idx)
                return False
        new_tag = self.assigned_tags.add()
        new_tag.addon_id = addon_id
        new_tag.category_name = category_name
        return True

    def remove_category_tags(self, category_name: str):
        """Removes all tag assignments for a category name."""
        indices_to_remove = [
            i for i, tag in enumerate(self.assigned_tags)
            if tag.category_name == category_name
        ]
        for i in reversed(indices_to_remove):
            self.assigned_tags.remove(i)

    def rename_category_tags(self, old_name: str, new_name: str):
        """Updates category name across all assigned tags."""
        for tag in self.assigned_tags:
            if tag.category_name == old_name:
                tag.category_name = new_name


classes = (
    CategoryItem,
    AddonCategoryTag,
    FilterPreset,
    AddonCategoriesPreferences,
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
