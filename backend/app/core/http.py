from typing import Any


def success_response(data: Any = None, message: str = "success", code: int = 200) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def paginated_response(items: list[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    return success_response(
        {
            "list": items,
            "total": total,
            "page": page,
            "pageSize": page_size,
        }
    )
