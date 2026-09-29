"""
User interface rendering for Add-on and Extension Categories in Blender Preferences.

Uses a virtualised UI_UL_list for the right-hand content area so scrolling
handles arbitrary item counts without manual pagination.
"""

import bpy
try:
    from .scanner import get_preferences, scan_all_addons, filter_addons
except (ImportError, ValueError):
    from scanner import get_preferences, scan_all_addons, filter_addons



# ---------------------------------------------------------------------------
# Virtualised list (UI_UL_list)
# ---------------------------------------------------------------------------

class CATEGORY_UL_addons(bpy.types.UIList):
    """UIList rendering each add-on / extension as a compact card row."""

    bl_idname = "CATEGORY_UL_addons"

    @classmethod
    def poll(cls, context):
        return get_preferences(context) is not None

    def draw_item(self, context, layout, _data, item, _icon,
                  _active_data, _active_propname, _index):
        if item is None:
            layout.label(text="", icon='BLANK1')
            return

        # === LEFT: action button (canto) ===
        left_col = layout.column(align=True)
        left_col.alignment = 'LEFT'
        if item.is_installed:
            toggle_icon = 'CHECKBOX_HLT' if item.is_enabled else 'CHECKBOX_DEHLT'
            toggle_op = left_col.operator(
                "addon_categories.toggle_addon",
                text="",
                icon=toggle_icon,
                depress=item.is_enabled,
            )
            toggle_op.module_name = item.id
        else:
            inst_op = left_col.operator(
                "addon_categories.install_remote",
                text="",
                icon='IMPORT',
            )
            inst_op.pkg_id = item.id
            inst_op.repo_directory = item.repo_directory

        # === MIDDLE: identity + meta ===
        mid_col = layout.column(align=True)
        title_row = mid_col.row(align=True)
        title_row.scale_y = 1.15
        addon_icon = 'SCRIPT' if item.is_installed else 'EXTENSION'
        # Title is no longer a click target — single-action contract.
        title_row.label(text=item.title, icon=addon_icon)

        meta_row = mid_col.row(align=True)
        meta_row.scale_y = 0.82
        raw_desc = (item.description or "").strip()
        if raw_desc:
            meta_row.label(text=raw_desc[:60] + ("…" if len(raw_desc) > 60 else ""))
        else:
            meta_row.label(text="Extension add-on", icon='BLANK1')

        if item.author:
            meta_row.label(text=f"by {item.author[:24]}")
        if item.version:
            meta_row.label(text=f"v{item.version}")

        # === RIGHT: tag chips ===
        right_col = layout.column(align=True)
        right_col.alignment = 'RIGHT'
        right_col.scale_y = 0.95

        visible_cats = item.assigned_categories[:2]
        overflow = max(0, len(item.assigned_categories) - len(visible_cats))

        for cat_name in visible_cats:
            chip_row = right_col.row(align=True)
            chip_row.scale_y = 0.85
            tag_btn = chip_row.operator(
                "addon_categories.toggle_tag",
                text=cat_name[:14] + ("…" if len(cat_name) > 14 else ""),
                icon='BOOKMARKS',
                emboss=False,
            )
            tag_btn.addon_id = item.id
            tag_btn.category_name = cat_name

        if overflow:
            chip_row = right_col.row(align=True)
            chip_row.scale_y = 0.85
            chip_row.label(text=f"+{overflow} more", icon='BOOKMARKS')

        if not item.assigned_categories:
            chip_row = right_col.row(align=True)
            chip_row.scale_y = 0.85
            chip_row.label(text="Add tag…", icon='BOOKMARKS')

        assign_btn = right_col.operator(
            "addon_categories.assign_popup",
            text="",
            icon='BOOKMARKS',
        )
        assign_btn.addon_id = item.id
        assign_btn.addon_title = item.title


# Module-level cache: UIList expects a CollectionProperty-like indexable
# container. We bridge AddonItemInfo (dataclass) → dict → keyed collection
# so template_list can iterate it.

_FILTERED_CACHE: dict[str, dict] = {}
_FILTERED_HASH: str = ""


def _cache_key(prefs) -> str:
    return "|".join([
        prefs.active_category or "All",
        prefs.search_query or "",
        prefs.status_filter or "ALL",
    ])


def _refresh_filtered_cache(context, prefs) -> list[dict]:
    """Rebuild the cache when filters change; returns flat list of dicts."""
    global _FILTERED_HASH
    key = _cache_key(prefs)
    if _FILTERED_HASH == key and _FILTERED_CACHE:
        return list(_FILTERED_CACHE.values())

    all_addons = scan_all_addons(context)
    filtered = filter_addons(
        all_addons,
        category=prefs.active_category,
        search_query=prefs.search_query,
        status_filter=prefs.status_filter,
    )
    _FILTERED_CACHE.clear()
    for item in filtered:
        _FILTERED_CACHE[item.id] = {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "author": item.author,
            "version": item.version,
            "is_installed": item.is_installed,
            "is_enabled": item.is_enabled,
            "is_extension": item.is_extension,
            "repo_directory": item.repo_directory,
            "raw_tags": list(item.raw_tags),
            "legacy_category": item.legacy_category,
            "assigned_categories": list(item.assigned_categories),
        }
    _FILTERED_HASH = key
    return list(_FILTERED_CACHE.values())


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def draw_category_manager(layout, context, prefs):
    """Draws the complete categories management interface."""
    prefs.ensure_default_categories()

    # Refresh virtualised cache (no-op if filters unchanged).
    all_addons = scan_all_addons(context)
    visible_items = _refresh_filtered_cache(context, prefs)

    active_cat = prefs.active_category or "All"

    # Item counts per category (always computed from the full set).
    cat_counts = {"All": len(all_addons)}
    for cat in prefs.categories:
        cat_counts[cat.name] = sum(1 for item in all_addons if cat.name in item.assigned_categories)

    # ----------------------------------------------------
    # Top Control Bar (Search, Filters, Bulk Actions, JSON)
    # ----------------------------------------------------
    top_box = layout.box()

    # Row 1: Search and Filters
    row1 = top_box.row(align=True)
    row1.prop(
        prefs, "search_query", text="", icon='VIEWZOOM',
        placeholder="Search title, author, tags, or description…",
    )
    if prefs.search_query:
        clear_op = row1.operator("addon_categories.select_category", text="", icon='PANEL_CLOSE')
        clear_op.category_name = active_cat  # Keep active cat, just gives a quick click target

    row1.separator(factor=2)
    row1.prop(prefs, "status_filter", text="")

    # Row 2: Bulk Category Actions & Tools
    row2 = top_box.row(align=True)

    # Active category bulk actions
    sub_bulk = row2.row(align=True)
    bulk_enable = sub_bulk.operator(
        "addon_categories.enable_category_all",
        text=f"Enable All ({active_cat})",
        icon='CHECKBOX_HLT',
    )
    bulk_enable.category_name = active_cat

    bulk_disable = sub_bulk.operator(
        "addon_categories.disable_category_all",
        text=f"Disable All ({active_cat})",
        icon='CHECKBOX_DEHLT',
    )
    bulk_disable.category_name = active_cat

    row2.separator(factor=2)

    # Tools: Export, Import. Reset (destructive) hides in the kebab menu.
    sub_tools = row2.row(align=True)
    sub_tools.operator("addon_categories.export_json", text="Export", icon='EXPORT')
    sub_tools.operator("addon_categories.import_json", text="Import", icon='IMPORT')
    sub_tools.popover(
        "addon_categories.PT_presets_menu",
        text="",
        icon='BOOKMARKS',
    )
    sub_tools.popover(
        "addon_categories.PT_tools_menu",
        text="",
        icon='COLLAPSEMENU',
    )

    layout.separator(factor=0.5)

    # ----------------------------------------------------
    # Main Body: Split Sidebar (Categories) & Content Area
    # ----------------------------------------------------
    split = layout.split(factor=0.23)

    # === LEFT: Category Sidebar ===
    left_col = split.column()
    sidebar_box = left_col.box()

    # "All Add-ons" item
    all_row = sidebar_box.row(align=True)
    all_row.scale_y = 1.0
    is_all_active = active_cat == "All"
    all_op = all_row.operator(
        "addon_categories.select_category",
        text=f"All Items ({cat_counts.get('All', 0)})",
        icon='FILE_TEXT',
        depress=is_all_active,
    )
    all_op.category_name = "All"

    sidebar_box.separator()

    # Header with "+ Add Category"
    header_row = sidebar_box.row(align=True)
    header_row.label(text="Categories", icon='BOOKMARKS')
    add_btn = header_row.operator("addon_categories.add_category", text="", icon='ADD')

    # Categories list
    cat_col = sidebar_box.column(align=True)
    for cat in prefs.categories:
        row = cat_col.row(align=True)
        row.scale_y = 1.15
        is_active = active_cat == cat.name
        count = cat_counts.get(cat.name, 0)
        display_label = f"{cat.name} ({count})"

        # Colour indicator — narrow tinted separator on the left edge.
        # Built-ins with a neutral (white) colour skip the swatch so legacy
        # serialised data does not render a visual artifact.
        is_neutral = all(abs(c - 1.0) < 1e-4 for c in cat.color[:3])
        if not is_neutral:
            swatch = row.column()
            swatch.scale_x = 0.18
            swatch.label(text=" ", icon='BLANK1')

        # Select button
        sel_op = row.operator(
            "addon_categories.select_category",
            text=display_label,
            icon=cat.icon or 'FOLDER_REDIRECT',
            depress=is_active,
        )
        sel_op.category_name = cat.name

        # Custom category controls (Rename / Delete / Reorder)
        if not cat.is_builtin:
            ren_op = row.operator("addon_categories.rename_category", text="", icon='GREASEPENCIL')
            ren_op.old_name = cat.name

            up_op = row.operator("addon_categories.move_category", text="", icon='TRIA_UP')
            up_op.category_name = cat.name
            up_op.direction = 'UP'

            down_op = row.operator("addon_categories.move_category", text="", icon='TRIA_DOWN')
            down_op.category_name = cat.name
            down_op.direction = 'DOWN'

            del_op = row.operator("addon_categories.remove_category", text="", icon='X')
            del_op.category_name = cat.name

    # === RIGHT: Virtualised list ===
    right_col = split.column()

    content_header = right_col.row(align=True)
    content_header.label(
        text=f"{active_cat} — {len(visible_items)} items found",
        icon='FILTER',
    )

    # When a single category is selected, show its accent colour strip
    # directly under the header so the user gets an unambiguous visual
    # link between sidebar selection and content area.
    if active_cat and active_cat != "All":
        for cat in prefs.categories:
            if cat.name == active_cat:
                is_neutral = all(abs(c - 1.0) < 1e-4 for c in cat.color[:3])
                if not is_neutral:
                    accent = right_col.row()
                    accent.scale_y = 0.05
                    accent.label(text=" ")
                break

    if not visible_items:
        empty_box = right_col.box()
        empty_col = empty_box.column(align=True)
        empty_col.scale_y = 1.5
        empty_col.label(text="No add-ons or extensions found matching current filter.", icon='INFO')
        return

    # Clamp list_index to a sane range (filters may have shrunk the list).
    if prefs.list_index >= len(visible_items):
        prefs.list_index = max(0, len(visible_items) - 1)

    # template_list handles virtualisation automatically — Blender only
    # renders the visible rows. No pagination, no cap, no extra clicks.
    right_col.template_list(
        "CATEGORY_UL_addons",
        "addon_categories_items",
        visible_items,
        "active_index",  # not used by UIList directly but required by API
        prefs,
        "list_index",
        rows=8,
        maxrows=20,
    )


class USERPREF_PT_addon_categories(bpy.types.Panel):
    """Add-on and Extension Categories Manager Panel"""
    bl_label = "Extension & Add-on Categories"
    bl_space_type = 'PREFERENCES'
    bl_region_type = 'WINDOW'
    bl_context = 'addons'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        prefs = get_preferences(context)
        if not prefs:
            self.layout.label(text="Categories preferences not initialized.")
            return

        draw_category_manager(self.layout, context, prefs)


class USERPREF_PT_tools_menu(bpy.types.Panel):
    """Popover menu for destructive / infrequent tools (granular resets)."""
    bl_label = "Tools"
    bl_space_type = 'PREFERENCES'
    bl_region_type = 'WINDOW'
    bl_context = 'addons'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        # Three granular destructive operations, separated by label clarity.
        col.operator(
            "addon_categories.reset_tags",
            text="Clear Tag Assignments",
            icon='BOOKMARKS',
        )
        col.operator(
            "addon_categories.reset_custom_categories",
            text="Remove Custom Categories",
            icon='FOLDER_REDIRECT',
        )
        col.separator()
        col.operator(
            "addon_categories.reset_defaults",
            text="Reset Everything",
            icon='RECOVER_LAST',
        )


class USERPREF_PT_presets_menu(bpy.types.Panel):
    """Popover for saved filter presets ('My Sculpting Setup', etc.)."""
    bl_label = "Filter Presets"
    bl_space_type = 'PREFERENCES'
    bl_region_type = 'WINDOW'
    bl_context = 'addons'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        prefs = get_preferences(context)
        if not prefs:
            return

        col = layout.column(align=True)

        # Save current filter state — always available.
        col.operator(
            "addon_categories.save_filter_preset",
            text="Save Current Filter…",
            icon='FILE_TICK',
        )
        col.separator()

        if not prefs.filter_presets:
            col.label(text="No saved presets yet.", icon='INFO')
            return

        # Apply / Remove for each saved preset.
        for preset in prefs.filter_presets:
            row = col.row(align=True)
            apply_op = row.operator(
                "addon_categories.apply_filter_preset",
                text=preset.name,
                icon='PLAY',
            )
            apply_op.preset_name = preset.name

            rm_op = row.operator(
                "addon_categories.remove_filter_preset",
                text="",
                icon='X',
            )
            rm_op.preset_name = preset.name


class CATEGORY_OT_open_manager(bpy.types.Operator):
    """Switch to Add-ons section and activate Categories View"""
    bl_idname = "addon_categories.open_manager"
    bl_label = "Open Category Manager"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        context.preferences.active_section = 'ADDONS'
        prefs = get_preferences(context)
        if prefs:
            prefs.view_mode = 'CATEGORIES'
        return {'FINISHED'}


def hook_header_switch(self, context):
    """Prepends category view switcher at top of Add-ons or Extensions panel."""
    prefs = get_preferences(context)
    if not prefs:
        return

    layout = self.layout
    box = layout.box()
    row = box.row(align=True)
    row.prop(prefs, "view_mode", expand=True)

    if prefs.view_mode == 'CATEGORIES':
        draw_category_manager(layout, context, prefs)
        # Visual separator before the default Blender list — context is obvious
        # from the panel below, so no explanatory label is needed.
        layout.separator(factor=2)


classes = (
    CATEGORY_UL_addons,
    USERPREF_PT_addon_categories,
    USERPREF_PT_tools_menu,
    USERPREF_PT_presets_menu,
    CATEGORY_OT_open_manager,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    # Hook into Preferences UI — only the Add-ons / Extensions panels.
    # Navigation-bar hook removed: redundant with the in-panel view-mode
    # switcher, and added visual noise to the side bar.
    try:
        from bl_ui import space_userpref
        if hasattr(space_userpref, "USERPREF_PT_addons"):
            space_userpref.USERPREF_PT_addons.prepend(hook_header_switch)
        if hasattr(space_userpref, "USERPREF_PT_extensions"):
            space_userpref.USERPREF_PT_extensions.prepend(hook_header_switch)
    except (ImportError, AttributeError) as e:
        # bl_ui internals are an implementation detail; failure here must not
        # block registration of the addon's own classes.
        print(f"Failed to hook preferences panels: {e}")


def unregister():
    # Remove hooks
    try:
        from bl_ui import space_userpref
        if hasattr(space_userpref, "USERPREF_PT_addons"):
            space_userpref.USERPREF_PT_addons.remove(hook_header_switch)
        if hasattr(space_userpref, "USERPREF_PT_extensions"):
            space_userpref.USERPREF_PT_extensions.remove(hook_header_switch)
    except (ImportError, AttributeError, ValueError):
        pass

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            # Class already unregistered or not yet registered — safe to ignore.
            pass
