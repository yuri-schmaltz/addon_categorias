"""
User interface rendering for Add-on and Extension Categories in Blender Preferences.
"""

import bpy
try:
    from .scanner import get_preferences, scan_all_addons, filter_addons
except (ImportError, ValueError):
    from scanner import get_preferences, scan_all_addons, filter_addons



def draw_category_manager(layout, context, prefs):
    """Draws the complete categories management interface."""
    prefs.ensure_default_categories()

    # Scan and filter add-ons
    all_addons = scan_all_addons(context)
    active_cat = prefs.active_category or "All"
    filtered = filter_addons(
        all_addons,
        category=active_cat,
        search_query=prefs.search_query,
        status_filter=prefs.status_filter,
    )

    # Calculate item counts per category for the badges
    cat_counts = {"All": len(all_addons)}
    for cat in prefs.categories:
        cat_counts[cat.name] = sum(1 for item in all_addons if cat.name in item.assigned_categories)

    # ----------------------------------------------------
    # Top Control Bar (Search, Filters, Bulk Actions, JSON)
    # ----------------------------------------------------
    top_box = layout.box()

    # Row 1: Search and Filters
    row1 = top_box.row(align=True)
    row1.prop(prefs, "search_query", text="", icon='VIEWZOOM', placeholder="Search add-ons or categories...")
    if prefs.search_query:
        clear_op = row1.operator("addon_categories.select_category", text="", icon='PANEL_CLOSE')
        clear_op.category_name = active_cat  # Keep active cat, just gives a quick click target

    row1.separator(factor=2)
    row1.prop(prefs, "status_filter", expand=True)

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

    # Tools: Export, Import, Reset
    sub_tools = row2.row(align=True)
    sub_tools.operator("addon_categories.export_json", text="Export JSON", icon='EXPORT')
    sub_tools.operator("addon_categories.import_json", text="Import JSON", icon='IMPORT')
    sub_tools.operator("addon_categories.reset_defaults", text="", icon='RECOVER_LAST')

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
    all_row.scale_y = 1.2
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

        # Select button
        sel_op = row.operator(
            "addon_categories.select_category",
            text=display_label,
            icon=cat.icon or 'FOLDER_REDIRECT',
            depress=is_active,
        )
        sel_op.category_name = cat.name

        # Custom category controls (Rename / Delete)
        if not cat.is_builtin:
            ren_op = row.operator("addon_categories.rename_category", text="", icon='GREASEPENCIL')
            ren_op.old_name = cat.name

            del_op = row.operator("addon_categories.remove_category", text="", icon='X')
            del_op.category_name = cat.name

    # === RIGHT: Add-ons & Extensions Cards ===
    right_col = split.column()

    # Title header
    content_header = right_col.row(align=True)
    content_header.label(
        text=f"{active_cat} — {len(filtered)} items found",
        icon='FILTER',
    )

    if not filtered:
        empty_box = right_col.box()
        empty_col = empty_box.column(align=True)
        empty_col.scale_y = 1.5
        empty_col.label(text="No add-ons or extensions found matching current filter.", icon='INFO')
        return

    # Render cards in a 4-column square block grid
    max_items = prefs.max_display_count
    visible_items = filtered[:max_items]
    NUM_COLS = 4

    for i in range(0, len(visible_items), NUM_COLS):
        chunk = visible_items[i : i + NUM_COLS]
        grid_row = right_col.row(align=False)

        for item in chunk:
            col = grid_row.column(align=True)
            card = col.box()

            # --- Row 1: Action (Enable/Disable/Install) + Version ---
            top_row = card.row(align=True)
            if item.is_installed:
                toggle_icon = 'CHECKBOX_HLT' if item.is_enabled else 'CHECKBOX_DEHLT'
                toggle_op = top_row.operator(
                    "addon_categories.toggle_addon",
                    text="Enabled" if item.is_enabled else "Disabled",
                    icon=toggle_icon,
                    depress=item.is_enabled,
                )
                toggle_op.module_name = item.id
            else:
                inst_op = top_row.operator(
                    "addon_categories.install_remote",
                    text="Install",
                    icon='IMPORT',
                )
                inst_op.pkg_id = item.id
                inst_op.repo_directory = item.repo_directory

            if item.version:
                v_box = top_row.row()
                v_box.alignment = 'RIGHT'
                v_box.label(text=f"v{item.version}")

            card.separator(factor=0.3)

            # --- Row 2: Addon Title ---
            title_row = card.row(align=True)
            title_row.scale_y = 1.15
            addon_icon = 'SCRIPT' if item.is_installed else 'EXTENSION'
            if item.is_installed:
                t_op = title_row.operator(
                    "addon_categories.toggle_addon",
                    text=item.title,
                    icon=addon_icon,
                    emboss=False,
                )
                t_op.module_name = item.id
            else:
                title_row.label(text=item.title, icon=addon_icon)

            # --- Rows 3 & 4: Description and Author ---
            desc_col = card.column(align=True)
            desc_col.scale_y = 0.82
            raw_desc = (item.description or "").strip()
            if raw_desc:
                desc_col.label(text=raw_desc[:40] + ("..." if len(raw_desc) > 40 else ""))
            else:
                desc_col.label(text="Extension add-on", icon='BLANK1')

            raw_author = (item.author or "").strip()
            if raw_author:
                desc_col.label(text=f"by {raw_author[:22]}")
            else:
                desc_col.label(text="")

            card.separator(factor=0.3)

            # --- Row 5: Tags and Add Category Button ---
            bot_row = card.row(align=True)
            if item.assigned_categories:
                first_cat = item.assigned_categories[0]
                tag_label = first_cat if len(first_cat) <= 12 else first_cat[:10] + ".."
                bot_row.label(text=tag_label, icon='BOOKMARKS')
                if len(item.assigned_categories) > 1:
                    bot_row.label(text=f"+{len(item.assigned_categories) - 1}")
            else:
                bot_row.label(text="Unassigned", icon='BOOKMARKS')

            assign_btn = bot_row.operator(
                "addon_categories.assign_popup",
                text="",
                icon='ADD',
            )
            assign_btn.addon_id = item.id
            assign_btn.addon_title = item.title

        # Pad remaining columns to enforce strict 25% equal width
        for _ in range(NUM_COLS - len(chunk)):
            grid_row.column(align=True)

    # Pagination: Load more button
    if len(filtered) > max_items:
        more_row = right_col.row()
        more_row.scale_y = 1.3
        remaining = len(filtered) - max_items
        more_btn = more_row.operator(
            "addon_categories.load_more",
            text=f"Show More... ({remaining} items remaining)",
            icon='DOWNARROW_HLT',
        )
        more_btn.step = 50


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


def hook_navigation_bar(self, context):
    """Appends quick access button in Preferences navigation bar."""
    prefs = get_preferences(context)
    if not prefs:
        return

    layout = self.layout
    layout.separator(factor=0.5)

    is_cat_view = (context.preferences.active_section == 'ADDONS' and prefs.view_mode == 'CATEGORIES')
    op = layout.operator(
        "addon_categories.open_manager",
        text="Categories",
        icon='FILTER',
        depress=is_cat_view,
    )


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
        # Add visual separator so default list below is clearly demarcated
        layout.separator(factor=2)
        sep_box = layout.box()
        sep_box.label(text="Standard Blender Add-ons / Extensions List Below", icon='SORTALPHA')


classes = (
    USERPREF_PT_addon_categories,
    CATEGORY_OT_open_manager,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    # Hook into Preferences UI
    try:
        from bl_ui import space_userpref
        if hasattr(space_userpref, "USERPREF_PT_navigation_bar"):
            space_userpref.USERPREF_PT_navigation_bar.append(hook_navigation_bar)
        if hasattr(space_userpref, "USERPREF_PT_addons"):
            space_userpref.USERPREF_PT_addons.prepend(hook_header_switch)
        if hasattr(space_userpref, "USERPREF_PT_extensions"):
            space_userpref.USERPREF_PT_extensions.prepend(hook_header_switch)
    except Exception as e:
        print(f"Failed to hook preferences panels: {e}")


def unregister():
    # Remove hooks
    try:
        from bl_ui import space_userpref
        if hasattr(space_userpref, "USERPREF_PT_navigation_bar"):
            space_userpref.USERPREF_PT_navigation_bar.remove(hook_navigation_bar)
        if hasattr(space_userpref, "USERPREF_PT_addons"):
            space_userpref.USERPREF_PT_addons.remove(hook_header_switch)
        if hasattr(space_userpref, "USERPREF_PT_extensions"):
            space_userpref.USERPREF_PT_extensions.remove(hook_header_switch)
    except Exception:
        pass

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
