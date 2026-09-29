"""
Scanner for installed add-ons, installed extensions, and repository packages.
"""

from dataclasses import dataclass, field
import addon_utils
import bpy
try:
    from .presets import match_default_categories
except (ImportError, ValueError):
    from presets import match_default_categories



@dataclass
class AddonItemInfo:
    id: str
    title: str
    description: str = ""
    author: str = ""
    version: str = ""
    is_installed: bool = True
    is_enabled: bool = False
    is_extension: bool = False
    repo_directory: str = ""
    repo_name: str = ""
    raw_tags: list[str] = field(default_factory=list)
    legacy_category: str = ""
    assigned_categories: list[str] = field(default_factory=list)


def get_preferences(context=None):
    """Retrieve addon preferences safely."""
    ctx = context or bpy.context
    addon_name = __package__ or "addon_categorias"
    prefs = ctx.preferences.addons.get(addon_name)
    if prefs and prefs.preferences:
        return prefs.preferences
    return None


def scan_all_addons(context=None) -> list[AddonItemInfo]:
    """
    Scans all add-ons: legacy add-ons, installed extensions, and remote repository packages.
    """
    prefs = get_preferences(context)
    if prefs:
        prefs.ensure_default_categories()

    installed_map: dict[str, AddonItemInfo] = {}

    # 1. Scan installed add-ons and extensions via addon_utils
    for mod in addon_utils.modules():
        mod_name = mod.__name__
        info = addon_utils.module_bl_info(mod)
        is_enabled, is_loaded = addon_utils.check(mod_name)
        is_extension = mod_name.startswith("bl_ext.")

        title = info.get("name") or mod_name
        description = info.get("description", "")
        author = info.get("author", "")
        version_tuple = info.get("version", ())
        version_str = ".".join(map(str, version_tuple)) if version_tuple else ""
        legacy_cat = info.get("category", "")
        raw_tags = list(info.get("tags") or [])

        # Addon identifier: short name for bl_ext if possible, or full module name
        addon_id = mod_name

        item = AddonItemInfo(
            id=addon_id,
            title=title,
            description=description,
            author=author,
            version=version_str,
            is_installed=True,
            is_enabled=bool(is_enabled),
            is_extension=is_extension,
            raw_tags=raw_tags,
            legacy_category=legacy_cat,
        )
        installed_map[addon_id] = item
        # Also store short id lookup (e.g. bl_ext.blender_org.print3d_toolbox -> print3d_toolbox)
        if is_extension:
            short_id = mod_name.split(".")[-1]
            installed_map[short_id] = item

    # 2. Scan remote extensions from repositories
    remote_items: list[AddonItemInfo] = []
    try:
        import bl_pkg
        from bl_pkg import bl_extension_ops

        store = bl_pkg.repo_cache_store_ensure()
        if not store.is_init():
            bl_extension_ops.repo_cache_store_refresh_from_prefs(store)

        for entry in getattr(store, "_repos", []):
            try:
                remote = entry.pkg_manifest_from_remote_ensure(error_fn=lambda msg: None)
            except Exception:
                remote = None

            if not remote:
                continue

            repo_dir = getattr(entry, "directory", "")

            for pkg_id, manifest in remote.items():
                # If already installed, update metadata if missing and continue
                if pkg_id in installed_map:
                    inst = installed_map[pkg_id]
                    if not inst.raw_tags and hasattr(manifest, "tags") and manifest.tags:
                        inst.raw_tags = list(manifest.tags)
                    continue

                title = getattr(manifest, "title", None) or pkg_id.replace("_", " ").title()
                tagline = getattr(manifest, "tagline", "") or getattr(manifest, "description", "")
                tags = list(getattr(manifest, "tags", ()) or ())
                pkg_type = getattr(manifest, "type", "add-on")
                if pkg_type != "add-on":
                    continue

                version_str = str(getattr(manifest, "version", ""))
                maintainer = getattr(manifest, "maintainer", "")

                remote_item = AddonItemInfo(
                    id=f"remote:{pkg_id}",
                    title=title,
                    description=tagline,
                    author=maintainer,
                    version=version_str,
                    is_installed=False,
                    is_enabled=False,
                    is_extension=True,
                    repo_directory=repo_dir,
                    raw_tags=tags,
                )
                remote_items.append(remote_item)
    except Exception:
        pass

    # Collect unique items (installed + remote non-installed)
    all_items: list[AddonItemInfo] = []
    seen_ids = set()

    for item in installed_map.values():
        if item.id not in seen_ids:
            seen_ids.add(item.id)
            all_items.append(item)

    for item in remote_items:
        if item.id not in seen_ids:
            seen_ids.add(item.id)
            all_items.append(item)

    # 3. Resolve categories for each item
    for item in all_items:
        if prefs:
            user_categories = prefs.get_addon_categories(item.id)
            if user_categories:
                item.assigned_categories = user_categories
                continue

        # If no user category explicitly set, calculate heuristic match
        auto_cats = match_default_categories(
            title=item.title,
            tags=item.raw_tags,
            legacy_category=item.legacy_category,
            description=item.description,
        )
        item.assigned_categories = sorted(list(auto_cats))

    # Sort alphabetically by title
    all_items.sort(key=lambda x: x.title.lower())
    return all_items


def filter_addons(
    items: list[AddonItemInfo],
    category: str = "All",
    search_query: str = "",
    status_filter: str = "ALL",
) -> list[AddonItemInfo]:
    """Filters addon list according to active category, status, and search query."""
    filtered = items

    # Category filter
    if category and category != "All":
        filtered = [item for item in filtered if category in item.assigned_categories]

    # Status filter
    if status_filter == "INSTALLED":
        filtered = [item for item in filtered if item.is_installed]
    elif status_filter == "ENABLED":
        filtered = [item for item in filtered if item.is_installed and item.is_enabled]
    elif status_filter == "DISABLED":
        filtered = [item for item in filtered if item.is_installed and not item.is_enabled]
    elif status_filter == "AVAILABLE":
        filtered = [item for item in filtered if not item.is_installed]

    # Search filter
    if search_query:
        q = search_query.strip().lower()
        filtered = [
            item for item in filtered
            if q in item.title.lower()
            or q in item.description.lower()
            or q in item.author.lower()
            or any(q in cat.lower() for cat in item.assigned_categories)
            or any(q in tag.lower() for tag in item.raw_tags)
        ]

    return filtered
