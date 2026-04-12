"""从 OpenAPI spec 生成 API Markdown 文档的工具函数"""


def _resolve_ref(ref_str: str, components: dict) -> dict | None:
    """Resolve a $ref string to the actual schema dict."""
    if not ref_str or not ref_str.startswith("#/components/schemas/"):
        return None
    name = ref_str.rsplit("/", 1)[-1]
    schemas = (components or {}).get("schemas", {})
    sch = schemas.get(name)
    if not sch:
        return None
    return dict(sch)  # copy


def _pick_best_from_anyof(anyof_list: list) -> dict | None:
    """Pick the most informative (non-null) schema from an anyOf list. FastAPI uses anyOf for Optional[T]."""
    for item in anyof_list or []:
        if not isinstance(item, dict):
            continue
        # skip plain {"type": "null"} - it just means the field can be null
        if item.get("type") == "null" and len(item.keys()) <= 2:
            continue
        return item
    return None


def _flatten_schema(schema: dict, components: dict, visited: set | None = None) -> dict:
    """
    Fully flatten a schema by resolving $ref, merging allOf, and unwrapping anyOf.
    Returns a plain dict with 'properties', 'required', etc. ready for field collection.
    """
    if not schema or not isinstance(schema, dict):
        return {}
    if visited is None:
        visited = set()

    # Step 0: unwrap anyOf -> pick the best non-null option (FastAPI uses anyOf for Optional[T])
    if schema.get("anyOf") and isinstance(schema["anyOf"], list):
        best = _pick_best_from_anyof(schema["anyOf"])
        if best:
            return _flatten_schema(best, components, visited)

    # Step 1: resolve top-level $ref
    if schema.get("$ref"):
        ref_name = schema["$ref"].rsplit("/", 1)[-1] if schema["$ref"].startswith("#/components/schemas/") else ""
        if ref_name in visited:
            return {}  # prevent circular
        visited = visited | {ref_name}
        ref_sch = _resolve_ref(schema["$ref"], components)
        if not ref_sch:
            return {}
        return _flatten_schema(ref_sch, components, visited)

    # Step 2: merge allOf
    if schema.get("allOf") and isinstance(schema["allOf"], list):
        merged_props: dict[str, dict] = {}
        merged_required: set[str] = set()
        for sub in schema["allOf"]:
            flat = _flatten_schema(sub, components, visited)
            if flat.get("properties"):
                for k, v in flat["properties"].items():
                    merged_props[k] = v
            if flat.get("required"):
                merged_required.update(flat["required"])
        result = {}
        if merged_props:
            result["properties"] = merged_props
        if merged_required:
            result["required"] = sorted(merged_required)
        return result

    # Step 3: return as-is (plain object with properties, or leaf type)
    return dict(schema)


def _get_type_display(schema: dict, components: dict) -> str:
    """Get human-readable type string for a schema."""
    if not schema or not isinstance(schema, dict):
        return "any"

    # handle anyOf (e.g. T | null from FastAPI Optional[T])
    if schema.get("anyOf") and isinstance(schema["anyOf"], list):
        best = _pick_best_from_anyof(schema["anyOf"])
        if best:
            return _get_type_display(best, components)

    # resolve ref first
    if schema.get("$ref"):
        ref_sch = _resolve_ref(schema["$ref"], components)
        if ref_sch:
            name = schema["$ref"].rsplit("/", 1)[-1]
            if ref_sch.get("properties") or ref_sch.get("allOf") or ref_sch.get("anyOf"):
                return f"object({name})"
            return name
        return "unknown"

    stype = schema.get("type")
    if stype == "array":
        items = schema.get("items")
        if items:
            return _get_type_display(items, components) + "[]"
        return "array"
    if stype in ("string", "integer", "number", "boolean", "file"):
        return stype
    if schema.get("allOf") or schema.get("anyOf"):
        return "object"
    if schema.get("properties"):
        return "object"
    return "any"


def _get_type_name(val: dict, components: dict) -> str | None:
    """Extract the schema/type name from a field value, e.g. 'DepartmentItem' from $ref or object(DepartmentItem)."""
    if not val or not isinstance(val, dict):
        return None
    if val.get("$ref") and val["$ref"].startswith("#/components/schemas/"):
        return val["$ref"].rsplit("/", 1)[-1]
    # For array types, look into items for the real type
    if val.get("type") == "array" and val.get("items"):
        return _get_type_name(val["items"], components)
    flat = _flatten_schema(val, components)
    ref_name = None
    if flat.get("$ref") and flat["$ref"].startswith("#/components/schemas/"):
        ref_name = flat["$ref"].rsplit("/", 1)[-1]
    # For allOf, pick the first $ref sub-item's name as the composite type name
    if not ref_name and flat.get("allOf"):
        for sub in flat["allOf"]:
            if isinstance(sub, dict) and sub.get("$ref") and sub["$ref"].startswith("#/components/schemas/"):
                ref_name = sub["$ref"].rsplit("/", 1)[-1]
                break
    return ref_name


def _collect_fields(schema: dict, components: dict, prefix: str, depth: int, seen_types: set[str] | None = None) -> list[dict]:
    """
    Recursively collect fields from a flattened schema.
    Each field dict: {key, full_path, title, desc, type, required, children}
    seen_types: set of schema names already shown; avoids re-expanding same type (e.g. DepartmentItem.children -> DepartmentItem).
    """
    if depth > 8 or not schema:
        return []
    if seen_types is None:
        seen_types = set()

    # Flatten first: resolve $ref + merge allOf + unwrap anyOf
    flat = _flatten_schema(schema, components)

    if not flat:
        return []

    props = flat.get("properties") or {}
    if not props:
        return []

    required_set = set(flat.get("required") or [])
    fields: list[dict] = []

    for key, val in props.items():
        if not isinstance(val, dict):
            continue
        full_path = f"{prefix}.{key}" if prefix else key
        title = val.get("title") or ""
        desc = val.get("description") or ""
        type_str = _get_type_display(val, components)
        is_req = key in required_set
        children: list[dict] = []

        # Decide whether to recurse into nested structures
        if depth < 6:
            type_name = _get_type_name(val, components)
            should_recurse = True
            if type_name and type_name in seen_types:
                # Same type already expanded above — skip to avoid repetitive nesting
                should_recurse = False

            if should_recurse:
                new_seen = seen_types | {type_name} if type_name else seen_types
                if val.get("properties") or val.get("$ref") or val.get("allOf") or val.get("anyOf"):
                    children = _collect_fields(val, components, full_path, depth + 1, new_seen)
                elif val.get("type") == "array" and val.get("items"):
                    children = _collect_fields(val["items"], components, full_path + "[]", depth + 1, new_seen)

        fields.append({
            "key": key,
            "full_path": full_path,
            "title": title,
            "desc": desc,
            "type": type_str,
            "required": is_req,
            "children": children,
        })

    return fields


def _fmt_fields(fields: list, indent: int) -> str:
    lines = []
    ind = "  " * indent
    for f in fields:
        mark = "" if f["required"] else "(opt)"
        line = f'{ind}- `{f["full_path"]}` ({f["type"]}) {mark}'
        if f["title"]:
            line += f" -- {f['title']}"
        if f["desc"]:
            line += f": {f['desc']}"
        lines.append(line)
        if f.get("children"):
            lines.append(_fmt_fields(f["children"], indent + 1))
    return "\n".join(lines)


def build_api_docs_md(openapi_schema: dict) -> str:
    """根据 OpenAPI schema 生成完整的 Markdown 接口文档。"""
    spec = openapi_schema
    paths = spec.get("paths", {})
    components = spec.get("components", {})
    lines = [f"# {spec.get('title', 'API')} Interface Reference\n"]

    for path_key in sorted(paths.keys()):
        path_item = paths[path_key]
        for method in ("get", "post", "put", "patch", "delete"):
            op = path_item.get(method)
            if not op:
                continue
            summary = op.get("summary") or ""
            method_upper = method.upper()

            lines.append(f"## **{method_upper}** `{path_key}`{f' -- {summary}' if summary else ''}\n")

            # ---- Request Parameters ----
            req_parts = []

            # 1. query/path/header params
            params = op.get("parameters") or []
            if params:
                plines = []
                for p in params:
                    pname = p.get("name") or ""
                    pin = (p.get("in") or "query").upper()
                    psch = p.get("schema") or {}
                    ptype = _get_type_display(psch, components)
                    preq = p.get("required", False)
                    pmark = "" if preq else "(opt)"
                    ptitle = p.get("title") or ""
                    pdesc = p.get("description") or ""
                    ln = f"- `{pname}` ({ptype}) {pmark} [{pin}]"
                    if ptitle:
                        ln += f" -- {ptitle}"
                    if pdesc:
                        ln += f": {pdesc}"
                    plines.append(ln)
                req_parts.append(("Request Parameters (Query/Path/Header)", "\n".join(plines)))

            # 2. request body
            rb = op.get("requestBody")
            if rb:
                content = (rb.get("content") or {}).get("application/json")
                if content:
                    sch = content.get("schema") or content
                    rf = _collect_fields(sch, components, "", 0)
                    if rf:
                        rftxt = "Content-Type: application/json\n\n" + _fmt_fields(rf, 0)
                        req_parts.append(("Request Body (JSON)", rftxt))

            if req_parts:
                for title, body in req_parts:
                    lines.append(f"### {title}")
                    lines.append(body)
                    lines.append("")
            else:
                lines.append("### Request Params\n(none)\n")

            # ---- Response Params ----
            resp200 = (op.get("responses") or {}).get("200")
            resp_content = None
            if resp200:
                rc = resp200.get("content") or {}
                resp_content = rc.get("application/json") or rc.get("*/*")

            if resp_content:
                rsch = resp_content.get("schema") or resp_content
                rs = _collect_fields(rsch, components, "", 0)
                lines.append("### Response Params")
                if rs:
                    lines.append(_fmt_fields(rs, 0))
                else:
                    lines.append("(none)")
                lines.append("")
            else:
                lines.append("### Response Params\n(none)\n")

            lines.append("---\n")

    return "\n".join(lines)
