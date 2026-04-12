from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.http import paginated_response, success_response
from app.models import Department, Role, RoleDepartment, RoleMenu, UserRole
from app.schemas import (
    ApiResponse,
    PageData,
    RoleDataScopeRequest,
    RoleDetail,
    RoleMenusRequest,
    RoleSummary,
    RoleUpsertRequest,
    StatusPatchRequest,
)
from app.services.serializers import serialize_role


router = APIRouter(prefix="/role", tags=["角色管理"])


def _role_detail_query():
    return (
        select(Role)
        .options(selectinload(Role.role_menus).selectinload(RoleMenu.menu))
        .options(selectinload(Role.role_departments).selectinload(RoleDepartment.department))
    )


def _get_role_or_404(db: DbSession, role_id: int) -> Role:
    role = db.scalar(_role_detail_query().where(Role.id == role_id))
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return role


def _assert_role_unique(db: DbSession, *, name: str, code: str, exclude_role_id: int | None = None) -> None:
    name_statement = select(Role).where(Role.name == name)
    code_statement = select(Role).where(Role.code == code)
    if exclude_role_id:
        name_statement = name_statement.where(Role.id != exclude_role_id)
        code_statement = code_statement.where(Role.id != exclude_role_id)
    if db.scalar(name_statement):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色名称已存在")
    if db.scalar(code_statement):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色编码已存在")


@router.get(
    "",
    summary="获取角色列表",
    response_model=ApiResponse[PageData[RoleSummary]],
)
def get_role_list(
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的角色数量"),
    name: str | None = Query(default=None, title="角色名称", description="按角色名称模糊搜索"),
    code: str | None = Query(default=None, title="角色编码", description="按角色编码模糊搜索"),
    status: int | None = Query(default=None, title="状态", description="按角色状态筛选"),
) -> dict:
    filters = []
    if name:
        filters.append(Role.name.ilike(f"%{name.strip()}%"))
    if code:
        filters.append(Role.code.ilike(f"%{code.strip()}%"))
    if status is not None:
        filters.append(Role.status == status)

    total = db.scalar(select(func.count()).select_from(Role).where(*filters)) or 0
    roles = db.scalars(
        select(Role)
        .where(*filters)
        .order_by(Role.sort.asc(), Role.id.asc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return paginated_response([serialize_role(role) for role in roles], total, page, pageSize)


@router.post(
    "",
    summary="创建角色",
    response_model=ApiResponse[RoleSummary],
)
def create_role(payload: RoleUpsertRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    _assert_role_unique(db, name=payload.name, code=payload.code)
    role = Role(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        data_scope=payload.dataScope,
        sort=payload.sort,
        status=payload.status,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return success_response(serialize_role(role), message="创建成功")


@router.get(
    "/{role_id}",
    summary="获取角色详情",
    response_model=ApiResponse[RoleDetail],
)
def get_role_detail(
    role_id: Annotated[int, Path(title="角色 ID", description="要查询的角色主键 ID")],
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    return success_response(serialize_role(_get_role_or_404(db, role_id), include_relations=True))


@router.patch(
    "/{role_id}",
    summary="更新角色",
    response_model=ApiResponse[RoleSummary],
)
def update_role(
    role_id: Annotated[int, Path(title="角色 ID", description="要更新的角色主键 ID")],
    payload: RoleUpsertRequest | StatusPatchRequest,
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    role = _get_role_or_404(db, role_id)
    if isinstance(payload, RoleUpsertRequest):
        _assert_role_unique(db, name=payload.name, code=payload.code, exclude_role_id=role_id)
        role.name = payload.name
        role.code = payload.code
        role.description = payload.description
        role.data_scope = payload.dataScope
        role.sort = payload.sort
        role.status = payload.status
    else:
        role.status = payload.status

    db.commit()
    db.refresh(role)
    return success_response(serialize_role(role), message="更新成功")


@router.delete(
    "/{role_id}",
    summary="删除角色",
    response_model=ApiResponse[None],
)
def delete_role(
    role_id: Annotated[int, Path(title="角色 ID", description="要删除的角色主键 ID")],
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    role = _get_role_or_404(db, role_id)
    if role.code == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统管理员角色不能删除")
    if db.scalar(select(UserRole).where(UserRole.role_id == role_id).limit(1)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色已分配给用户，不能删除")
    db.delete(role)
    db.commit()
    return success_response(message="删除成功")


@router.post(
    "/{role_id}/menus",
    summary="设置角色菜单权限",
    response_model=ApiResponse[RoleDetail],
)
def set_role_menus(
    role_id: Annotated[int, Path(title="角色 ID", description="要配置菜单权限的角色主键 ID")],
    payload: RoleMenusRequest,
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    role = _get_role_or_404(db, role_id)
    menu_ids = sorted(set(payload.menuIds))
    db.query(RoleMenu).filter(RoleMenu.role_id == role.id).delete()
    for menu_id in menu_ids:
        db.add(RoleMenu(role_id=role.id, menu_id=menu_id))
    db.commit()
    return success_response(serialize_role(_get_role_or_404(db, role.id), include_relations=True), message="权限配置成功")


@router.post(
    "/{role_id}/data-scope",
    summary="设置角色数据权限",
    response_model=ApiResponse[RoleDetail],
)
def set_role_data_scope(
    role_id: Annotated[int, Path(title="角色 ID", description="要配置数据权限的角色主键 ID")],
    payload: RoleDataScopeRequest,
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    role = _get_role_or_404(db, role_id)
    if payload.departmentIds:
        departments = db.scalars(select(Department.id).where(Department.id.in_(payload.departmentIds))).all()
        if sorted(departments) != sorted(set(payload.departmentIds)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="存在无效的部门ID")

    role.data_scope = payload.dataScope
    db.query(RoleDepartment).filter(RoleDepartment.role_id == role.id).delete()
    for department_id in sorted(set(payload.departmentIds)):
        db.add(RoleDepartment(role_id=role.id, department_id=department_id))
    db.commit()
    return success_response(serialize_role(_get_role_or_404(db, role.id), include_relations=True), message="数据权限更新成功")
