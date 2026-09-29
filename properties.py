"""
Data models and preferences properties for Add-on and Extension Categories.
"""

import bpy
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    EnumProperty,
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


class AddonCategoryTag(bpy.types.PropertyGroup):
    addon_id: StringProperty(name="Add-on ID", default="")
    category_name: StringProperty(name="Category Name", default="")


class AddonCategoriesPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__ or "addon_categorias"

    categories: CollectionProperty(type=CategoryItem)
    assigned_tags: CollectionProperty(type=AddonCategoryTag)

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

    max_display_count: IntProperty(
        name="Show Items Limit",
        description="Limit number of items rendered to preserve UI performance",
        default=60,
        min=20,
        max=500,
    )

    def ensure_default_categories(self):
        """Populate default categories if not already present."""
        existing_names = {c.name for c in self.categories}
        for idx, (cid, name, icon, desc) in enumerate(DEFAULT_CATEGORIES):
            if name not in existing_names:
                item = self.categories.add()
                item.name = name
                item.icon = icon
                item.is_builtin = True
                item.order = idx
                item.description = desc

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
        except Exception:
            pass
