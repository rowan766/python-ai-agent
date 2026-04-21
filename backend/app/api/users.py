from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.http import paginated_response, success_response
from app.core.security import hash_password, verify_password
from app.models import Department, Menu, Role, RoleMenu, User, UserRole
from app.schemas import (
    ApiResponse,
    AdminChangePasswordRequest,
    AssignRolesRequest,
    ChangePasswordRequest,
    MenuItem,
    PageData,
    ProfileUpdateRequest,
    UserItem,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.services.serializers import build_tree, serialize_menu, serialize_user


router = APIRouter(prefix="/user", tags=["用户管理"])


def _user_detail_query():
    return (
        select(User)
        .options(selectinload(User.department))
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    )


def _get_user_or_404(db: DbSession, user_id: int) -> User:
    user = db.scalar(_user_detail_query().where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


def _assert_email_unique(db: DbSession, email: str | None, exclude_user_id: int | None = None) -> None:
    if not email:
        return
    statement = select(User).where(User.email == email)
    if exclude_user_id:
        statement = statement.where(User.id != exclude_user_id)
    if db.scalar(statement):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")


def _assert_username_unique(db: DbSession, username: str, exclude_user_id: int | None = None) -> None:
    statement = select(User).where(User.username == username)
    if exclude_user_id:
        statement = statement.where(User.id != exclude_user_id)
    if db.scalar(statement):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")


def _collect_department_ids(db: DbSession, department_id: int) -> list[int]:
    children = db.scalars(select(Department.id).where(Department.parent_id == department_id)).all()
    result = [department_id]
    for child_id in children:
        result.extend(_collect_department_ids(db, child_id))
    return result


@router.get(
    "",
    summary="获取用户列表",
    response_model=ApiResponse[PageData[UserItem]],
)
def get_user_list(
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的用户数量"),
    username: str | None = Query(default=None, title="用户名", description="按用户名模糊搜索"),
    email: str | None = Query(default=None, title="邮箱", description="按邮箱模糊搜索"),
    departmentId: int | None = Query(default=None, title="部门 ID", description="按部门及其子部门筛选"),
) -> dict:
    filters = []
    if username:
        filters.append(User.username.ilike(f"%{username.strip()}%"))
    if email:
        filters.append(User.email.ilike(f"%{email.strip()}%"))
    if departmentId is not None:
        filters.append(User.department_id.in_(_collect_department_ids(db, departmentId)))

    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    users = (
        db.scalars(
            _user_detail_query()
            .where(*filters)
            .order_by(User.id.asc())
            .offset((page - 1) * pageSize)
            .limit(pageSize)
        )
        .unique()
        .all()
    )
    return paginated_response([serialize_user(user) for user in users], total, page, pageSize)


@router.post(
    "",
    summary="创建用户",
    response_model=ApiResponse[UserItem],
)
def create_user(payload: UserCreateRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    _assert_username_unique(db, payload.username)
    _assert_email_unique(db, payload.email)

    user = User(
        username=payload.username,
        nickname=payload.username,
        email=payload.email,
        department_id=payload.departmentId,
        status=payload.status,
        password=hash_password(payload.password),
        gender=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return success_response(serialize_user(_get_user_or_404(db, user.id)), message="创建成功")


@router.get(
    "/profile",
    summary="获取个人信息",
    response_model=ApiResponse[UserItem],
)
def get_current_profile(db: DbSession, current_user: CurrentUser) -> dict:
    user = _get_user_or_404(db, current_user.id)
    return success_response(serialize_user(user))


@router.put(
    "/profile",
    summary="更新个人信息",
    response_model=ApiResponse[UserItem],
)
def update_current_profile(payload: ProfileUpdateRequest, db: DbSession, current_user: CurrentUser) -> dict:
    _assert_email_unique(db, payload.email, exclude_user_id=current_user.id)

    current_user.nickname = payload.nickname
    current_user.email = payload.email
    current_user.phone = payload.phone
    current_user.gender = payload.gender
    db.commit()
    db.refresh(current_user)
    return success_response(serialize_user(_get_user_or_404(db, current_user.id)), message="保存成功")


@router.post(
    "/change-password",
    summary="修改个人密码",
    response_model=ApiResponse[None],
)
def change_current_password(payload: ChangePasswordRequest, db: DbSession, current_user: CurrentUser) -> dict:
    if payload.newPassword != payload.confirmPassword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="两次输入的新密码不一致")
    if not verify_password(payload.oldPassword, current_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")

    current_user.password = hash_password(payload.newPassword)
    db.commit()
    return success_response(message="密码修改成功")


@router.get(
    "/current/menus",
    summary="获取当前用户菜单",
    response_model=ApiResponse[list[MenuItem]],
)
def get_current_user_menus(db: DbSession, current_user: CurrentUser) -> dict:
    role_ids = [relation.role_id for relation in current_user.user_roles]
    if not role_ids:
        return success_response([])

    menu_ids = db.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id.in_(role_ids))).all()
    if not menu_ids:
        return success_response([])

    menus = db.scalars(select(Menu).where(Menu.id.in_(menu_ids)).order_by(Menu.sort.asc(), Menu.id.asc())).all()
    tree = build_tree([serialize_menu(menu) for menu in menus])
    return success_response(tree)


@router.get(
    "/{user_id}",
    summary="获取用户详情",
    response_model=ApiResponse[UserItem],
)
def get_user_detail(
    user_id: Annotated[int, Path(title="用户 ID", description="要查询的用户主键 ID")],
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    return success_response(serialize_user(_get_user_or_404(db, user_id)))


@router.put(
    "/{user_id}",
    summary="更新用户",
    response_model=ApiResponse[UserItem],
)
def update_user(
    user_id: Annotated[int, Path(title="用户 ID", description="要更新的用户主键 ID")],
    payload: UserUpdateRequest,
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    user = _get_user_or_404(db, user_id)
    _assert_username_unique(db, payload.username, exclude_user_id=user_id)
    _assert_email_unique(db, payload.email, exclude_user_id=user_id)

    user.username = payload.username
    user.email = payload.email
    user.department_id = payload.departmentId
    user.status = payload.status
    if not user.nickname:
        user.nickname = payload.username

    db.commit()
    db.refresh(user)
    return success_response(serialize_user(_get_user_or_404(db, user_id)), message="更新成功")


@router.delete(
    "/{user_id}",
    summary="删除用户",
    response_model=ApiResponse[None],
)
def delete_user(
    user_id: Annotated[int, Path(title="用户 ID", description="要删除的用户主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录用户")
    user = _get_user_or_404(db, user_id)
    if user.username == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统内置管理员不能删除")
    db.delete(user)
    db.commit()
    return success_response(message="删除成功")


@router.post(
    "/{user_id}/roles",
    summary="分配用户角色",
    response_model=ApiResponse[UserItem],
)
def assign_user_roles(
    user_id: Annotated[int, Path(title="用户 ID", description="要分配角色的用户主键 ID")],
    payload: AssignRolesRequest,
    db: DbSession,
    _current_user: CurrentUser,
) -> dict:
    user = _get_user_or_404(db, user_id)
    role_ids = sorted(set(payload.roleIds))
    if role_ids:
        roles = db.scalars(select(Role).where(Role.id.in_(role_ids))).all()
        found_ids = sorted(role.id for role in roles)
        if found_ids != role_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="存在无效的角色ID")

    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    for role_id in role_ids:
        db.add(UserRole(user_id=user.id, role_id=role_id))
    db.commit()
    return success_response(serialize_user(_get_user_or_404(db, user.id)), message="角色分配成功")


@router.post(
    "/{user_id}/password",
    summary="修改用户密码",
    response_model=ApiResponse[None],
)
def change_user_password(
    user_id: Annotated[int, Path(title="用户 ID", description="要修改密码的用户主键 ID")],
    payload: AdminChangePasswordRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请在个人中心修改当前登录用户密码")
    if payload.newPassword != payload.confirmPassword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="两次输入的新密码不一致")

    user = _get_user_or_404(db, user_id)
    user.password = hash_password(payload.newPassword)
    db.commit()
    return success_response(message="密码修改成功")
