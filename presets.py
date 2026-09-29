"""
Default categories and auto-tagging heuristics for Blender Add-ons and Extensions.
"""

# Default categories: (ID, Display Name, Icon, Description, Color RGBA)
# Colors are accent hues used by the sidebar indicator. Saturation is kept
# moderate to remain readable against Blender's dark/light UI themes.
DEFAULT_CATEGORIES = [
    ("favorites",        "Favorites",          "SOLO_ON",            "Favorite and frequently used add-ons",                                                            (1.00, 0.85, 0.20, 1.0)),
    ("modeling",         "Modeling",           "MESH_CUBE",          "Mesh editing, hard-surface, curves and modifiers",                                                (0.40, 0.70, 1.00, 1.0)),
    ("sculpting",        "Sculpting",          "SCULPTMODE_HLT",     "Sculpting tools, brushes, and detailing",                                                          (1.00, 0.55, 0.30, 1.0)),
    ("rigging",          "Rigging & Armature", "ARMATURE_DATA",      "Character rigging, bone setups, and skins",                                                       (0.75, 0.55, 1.00, 1.0)),
    ("animation",        "Animation",          "ACTION",             "Animation workflows, keyframing, and motion tools",                                              (0.30, 0.95, 0.65, 1.0)),
    ("render_lighting",  "Render & Lighting",  "SHADING_RENDERED",   "Lighting setups, render engines, and camera tools",                                               (1.00, 0.85, 0.50, 1.0)),
    ("materials_shading","Materials & Shading","MATERIAL",           "Shaders, texture mapping, and node tools",                                                        (0.95, 0.50, 0.75, 1.0)),
    ("uv_texturing",     "UV & Texturing",     "UV",                 "UV unwrapping, layout, and packing",                                                              (0.55, 0.85, 0.95, 1.0)),
    ("import_export",    "Import & Export",    "IMPORT",             "File formats, I/O pipelines, and asset exchanges",                                                (0.70, 0.70, 0.70, 1.0)),
    ("pipeline_utils",   "Pipeline & Utilities","PREFERENCES",        "Productivity helpers, UI enhancements, and system tools",                                        (0.65, 0.65, 0.65, 1.0)),
]

# Keyword rules for automatic category matching
CATEGORY_RULES = {
    "Modeling": [
        "mesh", "modeling", "model", "curve", "surface", "boolean", "bool",
        "topology", "retopo", "loop", "poly", "extrude", "bevel", "modifier",
        "cad", "subdivision", "3d print", "fluent"
    ],
    "Sculpting": [
        "sculpt", "brush", "clay", "multires", "voxel", "remesh", "detail"
    ],
    "Rigging & Armature": [
        "rig", "rigging", "armature", "bone", "skinning", "weight", "pose",
        "jiggle", "hair bone", "ik", "fk", "mocap"
    ],
    "Animation": [
        "anim", "animation", "motion", "keyframe", "timeline", "action",
        "fcurve", "graph", "nla", "stop motion", "gif"
    ],
    "Render & Lighting": [
        "render", "lighting", "light", "camera", "cycles", "eevee", "compositor",
        "rebake", "baking", "hdri", "exposure", "illumination"
    ],
    "Materials & Shading": [
        "material", "materials", "shader", "shading", "texture", "textures",
        "node", "nodes", "matwerk", "pbr", "palette", "color"
    ],
    "UV & Texturing": [
        "uv", "uvs", "unwrap", "seam", "texture pack", "uv layout"
    ],
    "Import & Export": [
        "import", "export", "io", "fbx", "obj", "gltf", "svg", "bvh",
        "alembic", "usd", "stl", "ply", "dxf", "importer", "exporter"
    ],
    "Pipeline & Utilities": [
        "pipeline", "utility", "utilities", "system", "clean", "cleaner",
        "manager", "mcp", "batch", "toolbox", "align", "naming", "pie",
        "customizer", "interface", "shortcut", "organizer", "math", "development"
    ],
}


def match_default_categories(title: str, tags: list[str] | None, legacy_category: str | None, description: str = "") -> set[str]:
    """
    Returns matched category names based on metadata.
    """
    matched = set()
    text_corpus = f"{title} {legacy_category or ''} {' '.join(tags or [])} {description}".lower()

    # Exact legacy category matching first
    legacy_norm = (legacy_category or "").strip().lower()
    if legacy_norm:
        if "mesh" in legacy_norm or "model" in legacy_norm or "add mesh" in legacy_norm or "curve" in legacy_norm:
            matched.add("Modeling")
        elif "sculpt" in legacy_norm:
            matched.add("Sculpting")
        elif "rig" in legacy_norm or "armature" in legacy_norm:
            matched.add("Rigging & Armature")
        elif "anim" in legacy_norm:
            matched.add("Animation")
        elif "render" in legacy_norm or "lighting" in legacy_norm:
            matched.add("Render & Lighting")
        elif "material" in legacy_norm or "shader" in legacy_norm or "node" in legacy_norm or "paint" in legacy_norm:
            matched.add("Materials & Shading")
        elif "uv" in legacy_norm:
            matched.add("UV & Texturing")
        elif "import" in legacy_norm or "export" in legacy_norm:
            matched.add("Import & Export")
        elif "system" in legacy_norm or "development" in legacy_norm or "user interface" in legacy_norm:
            matched.add("Pipeline & Utilities")

    # Match by explicit extension tags
    if tags:
        for tag in tags:
            tag_lower = tag.lower()
            for cat_name, keywords in CATEGORY_RULES.items():
                if any(kw in tag_lower for kw in keywords):
                    matched.add(cat_name)

    # Keyword match from title/description if still empty
    if not matched:
        for cat_name, keywords in CATEGORY_RULES.items():
            if any(kw in text_corpus for kw in keywords):
                matched.add(cat_name)

    # Fallback to Pipeline & Utilities if nothing matched
    if not matched:
        matched.add("Pipeline & Utilities")

    return matched
