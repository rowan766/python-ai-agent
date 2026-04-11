from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.http import paginated_response, success_response
from app.core.security import hash_password, verify_password
from app.models import Department, Menu, Role, RoleMenu, User, UserRole
from app.schemas import (
    AssignRolesRequest,
    ChangePasswordRequest,
    ProfileUpdateRequest,
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


@router.get("", summary="获取用户列表")
def get_user_list(
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=1000),
    username: str | None = None,
    email: str | None = None,
    departmentId: int | None = None,
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


@router.post("", summary="创建用户")
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


@router.get("/profile", summary="获取个人信息")
def get_current_profile(db: DbSession, current_user: CurrentUser) -> dict:
    user = _get_user_or_404(db, current_user.id)
    return success_response(serialize_user(user))


@router.put("/profile", summary="更新个人信息")
def update_current_profile(payload: ProfileUpdateRequest, db: DbSession, current_user: CurrentUser) -> dict:
    _assert_email_unique(db, payload.email, exclude_user_id=current_user.id)

    current_user.nickname = payload.nickname
    current_user.email = payload.email
    current_user.phone = payload.phone
    current_user.gender = payload.gender
    db.commit()
    db.refresh(current_user)
    return success_response(serialize_user(_get_user_or_404(db, current_user.id)), message="保存成功")


@router.post("/change-password", summary="修改个人密码")
def change_current_password(payload: ChangePasswordRequest, db: DbSession, current_user: CurrentUser) -> dict:
    if payload.newPassword != payload.confirmPassword:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="两次输入的新密码不一致")
    if not verify_password(payload.oldPassword, current_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")

    current_user.password = hash_password(payload.newPassword)
    db.commit()
    return success_response(message="密码修改成功")


@router.get("/current/menus", summary="获取当前用户菜单")
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


@router.get("/{user_id}", summary="获取用户详情")
def get_user_detail(user_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    return success_response(serialize_user(_get_user_or_404(db, user_id)))


@router.put("/{user_id}", summary="更新用户")
def update_user(user_id: int, payload: UserUpdateRequest, db: DbSession, _current_user: CurrentUser) -> dict:
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


@router.delete("/{user_id}", summary="删除用户")
def delete_user(user_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录用户")
    user = _get_user_or_404(db, user_id)
    if user.username == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统内置管理员不能删除")
    db.delete(user)
    db.commit()
    return success_response(message="删除成功")


@router.post("/{user_id}/roles", summary="分配用户角色")
def assign_user_roles(user_id: int, payload: AssignRolesRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    user = _get_user_or_404(db, user_id)
    role_ids = sorted(set(payload.roleIds))
    if role_ids:
        roles = db.scalars(select(Role).where(Role.id.in_(role_ids))).all()
        found_ids = sorted(role.id for role in roles)
        if found_ids != role_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="存在无效的角色ID")

    db.query(UserRole).filter(UserRole.user_id == user.id).delete()
    for role_id in role_ids:
        db.add(UserRole(user_id=user.id, role_id=role_id))
    db.commit()
    return success_response(serialize_user(_get_user_or_404(db, user.id)), message="角色分配成功")
