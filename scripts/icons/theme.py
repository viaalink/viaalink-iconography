"""
The icon theme: one JSON file with everything brand- or look-specific (colours, fonts, logo,
camera, light rig, materials, canvas, gate, diagram look). Python side of the one loader per
language (TypeScript: scripts/icons/theme.ts).

    THEME = theme.load()            # $VIA_ICON_THEME, else theme/brand.json
    THEME["camera"]["azimuth"]
    theme.resolve(THEME, THEME["fonts"]["mono"])   # paths in the theme are relative to the file

The theme is validated against theme/brand.schema.json (a small JSON-schema subset, no
dependencies, so it runs in Blender's Python as well): a missing key or a wrong type stops the
run with the path of the problem instead of a KeyError deep inside a model.
"""

import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT = os.path.join(REPO, "theme", "brand.json")
SCHEMA = os.path.join(REPO, "theme", "brand.schema.json")
ENV = "VIA_ICON_THEME"

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
}


class ThemeError(ValueError):
    pass


def _check(value, schema, where, errors):
    kind = schema.get("type")
    if kind:
        ok = isinstance(value, _TYPES[kind]) and not (kind in ("integer", "number") and isinstance(value, bool))
        if not ok:
            errors.append(f"{where}: expected {kind}, got {type(value).__name__}")
            return
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        errors.append(f"{where}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in value:
                errors.append(f"{where}.{k}: missing")
        extra = schema.get("additionalProperties")
        for k, v in value.items():
            if k in props:
                _check(v, props[k], f"{where}.{k}", errors)
            elif isinstance(extra, dict):
                _check(v, extra, f"{where}.{k}", errors)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            errors.append(f"{where}: {len(value)} items")
        if "items" in schema:
            for i, v in enumerate(value):
                _check(v, schema["items"], f"{where}[{i}]", errors)


def validate(theme, schema=None):
    """Raise ThemeError listing every problem; returns the theme."""
    if schema is None:
        with open(SCHEMA, encoding="utf-8") as f:
            schema = json.load(f)
    errors = []
    _check(theme, schema, "theme", errors)
    if not errors:  # cross-references the schema cannot express
        hexes = theme["colors25d"]["hex"]
        for mode, roles in theme["colors25d"]["roles"].items():
            for role, name in roles.items():
                if name not in hexes:
                    errors.append(f"theme.colors25d.roles.{mode}.{role}: {name!r} is not in colors25d.hex")
    if errors:
        raise ThemeError("invalid icon theme:\n  " + "\n  ".join(errors))
    return theme


def theme_path():
    return os.environ.get(ENV) or DEFAULT


def load(path=None):
    """Load and validate the theme. `_file` and `_dir` are added for resolve()."""
    path = os.path.abspath(path or theme_path())
    with open(path, encoding="utf-8") as f:
        theme = json.load(f)
    validate(theme)
    theme["_file"] = path
    theme["_dir"] = os.path.dirname(path)
    return theme


def resolve(theme, rel):
    """A path from the theme (fonts, logo), relative to the theme file."""
    return rel if os.path.isabs(rel) else os.path.normpath(os.path.join(theme["_dir"], rel))


def palettes(theme):
    """{mode: {role: hex}} for the 2.5D materials."""
    hexes = theme["colors25d"]["hex"]
    return {mode: {role: hexes[name] for role, name in roles.items()} for mode, roles in theme["colors25d"]["roles"].items()}


if __name__ == "__main__":  # python3 scripts/icons/theme.py [file]: validate a theme
    import sys

    t = load(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"theme ok: {t['_file']} ({t['brand']['name']})")
