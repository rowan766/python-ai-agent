from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.http import success_response
from app.models import Menu
from app.schemas import ApiResponse, MenuItem, MenuUpsertRequest, StatusPatchRequest
from app.services.serializers import serialize_menu


router = APIRouter(prefix="/menu", tags=["菜单管理"])


def _get_menu_or_404(db: DbSession, menu_id: int) -> Menu:
    menu = db.scalar(select(Menu).where(Menu.id == menu_id))
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="菜单不存在")
    return menu


def _validate_menu_payload(payload: MenuUpsertRequest, *, current_id: int | None = None) -> None:
    if payload.type not in {"menu", "button"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="菜单类型必须是 menu 或 button")
    if payload.type == "menu" and (not payload.name or not payload.path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="菜单类型必须填写路由名称和路径")
    if payload.type == "button" and not payload.permission:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="按钮类型必须填写权限标识")
    if current_id and payload.parentId == current_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上级菜单不能选择自己")


def _collect_descendant_ids(db: DbSession, menu_id: int) -> list[int]:
    children = db.scalars(select(Menu.id).where(Menu.parent_id == menu_id)).all()
    result = [menu_id]
    for child_id in children:
        result.extend(_collect_descendant_ids(db, child_id))
    return result


@router.get(
    "",
    summary="获取菜单列表",
    response_model=ApiResponse[list[MenuItem]],
)
def get_menu_list(db: DbSession, _current_user: CurrentUser) -> dict:
    menus = db.scalars(select(Menu).order_by(Menu.sort.asc(), Menu.id.asc())).all()
    return success_response([serialize_menu(menu) for menu in menus])


@router.post(
    "",
    summary="创建菜单",
    response_model=ApiResponse[MenuItem],
)
def create_menu(payload: MenuUpsertRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    _validate_menu_payload(payload)
    menu = Menu(
        parent_id=payload.parentId,
        name=payload.name or payload.permission or payload.title,
        title=payload.title,
        type=payload.type,
        path=payload.path,
        component=payload.component,
        permission=payload.permission,
        icon=payload.icon,
        sort=payload.sort,
        visible=payload.visible if payload.type == "menu" else 1,
        status=payload.status,
    )
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return success_response(serialize_menu(menu), message="创建成功")


@router.get(
    "/{menu_id}",
    summary="获取菜单详情",
    response_model=ApiResponse[MenuItem],
)
def get_menu_detail(
    menu_id: Annotated[int, Path(title="菜单 ID", description="要查询的菜单主键 ID")],
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    return success_response(serialize_menu(_get_menu_or_404(db, menu_id)))


@router.put(
    "/{menu_id}",
    summary="更新菜单",
    response_model=ApiResponse[MenuItem],
)
def update_menu(
    menu_id: Annotated[int, Path(title="菜单 ID", description="要更新的菜单主键 ID")],
    payload: MenuUpsertRequest,
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    _validate_menu_payload(payload, current_id=menu_id)
    menu = _get_menu_or_404(db, menu_id)
    menu.parent_id = payload.parentId
    menu.name = payload.name or payload.permission or payload.title
    menu.title = payload.title
    menu.type = payload.type
    menu.path = payload.path
    menu.component = payload.component
    menu.permission = payload.permission
    menu.icon = payload.icon
    menu.sort = payload.sort
    menu.visible = payload.visible if payload.type == "menu" else 1
    menu.status = payload.status
    db.commit()
    db.refresh(menu)
    return success_response(serialize_menu(menu), message="更新成功")


@router.patch(
    "/{menu_id}",
    summary="更新菜单状态",
    response_model=ApiResponse[MenuItem],
)
def patch_menu_status(
    menu_id: Annotated[int, Path(title="菜单 ID", description="要更新状态的菜单主键 ID")],
    payload: StatusPatchRequest,
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    menu = _get_menu_or_404(db, menu_id)
    menu.status = payload.status
    db.commit()
    db.refresh(menu)
    return success_response(serialize_menu(menu), message="状态更新成功")


@router.delete(
    "/{menu_id}",
    summary="删除菜单",
    response_model=ApiResponse[None],
)
def delete_menu(
    menu_id: Annotated[int, Path(title="菜单 ID", description="要删除的菜单主键 ID")],
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    descendant_ids = _collect_descendant_ids(db, menu_id)
    menus = db.scalars(select(Menu).where(Menu.id.in_(descendant_ids))).all()
    if not menus:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="菜单不存在")
    for menu in menus:
        db.delete(menu)
    db.commit()
    return success_response(message="删除成功")
