"""
Extension & Add-on Categories for Blender 3D.
"""

bl_info = {
    "name": "Extension & Add-on Categories",
    "author": "Yuri & Antigravity",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "Preferences > Add-ons / Get Extensions",
    "description": "Categorize, organize, and filter Blender add-ons and extensions with custom tags, bulk controls, and JSON export/import.",
    "warning": "",
    "doc_url": "",
    "category": "System",
}

import sys

# Support module reload in Blender
if "properties" in locals():
    import importlib
    properties = importlib.reload(properties)
    operators = importlib.reload(operators)
    ui = importlib.reload(ui)
else:
    from . import properties
    from . import operators
    from . import ui


def register():
    properties.register()
    operators.register()
    ui.register()


def unregister():
    ui.unregister()
    operators.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
