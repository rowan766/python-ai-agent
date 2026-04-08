from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, is_platform_admin
from app.core.database import get_db
from app.models.department import Department, DepartmentMembership
from app.models.user import User

router = APIRouter()


class UserStatusUpdateRequest(BaseModel):
    is_active: bool


class UserMembershipItem(BaseModel):
    department_id: int
    is_primary: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "department_id": 2,
                "is_primary": True,
            }
        }
    )


class UserMembershipUpdateRequest(BaseModel):
    memberships: list[UserMembershipItem]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "memberships": [
                    {"department_id": 2, "is_primary": True},
                    {"department_id": 3, "is_primary": False},
                ]
            }
        }
    )


def ensure_platform_admin_access(current_user: User) -> None:
    if not is_platform_admin(current_user):
        raise HTTPException(status_code=403, detail="仅平台管理员可以管理用户")


def serialize_membership_row(
    membership: DepartmentMembership,
    department: Department,
) -> dict[str, Any]:
    return {
        "id": membership.id,
        "department_id": department.id,
        "department_name": department.name,
        "department_code": department.code,
        "membership_type": membership.membership_type,
        "is_primary": membership.is_primary,
        "status": membership.status,
    }


def build_user_row(
    user: User,
    memberships: list[dict[str, Any]],
    managed_departments: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "is_platform_admin": is_platform_admin(user),
        "organization_status": "ready" if memberships else "pending_assignment",
        "memberships": memberships,
        "managed_departments": managed_departments,
        "created_at": user.created_at,
    }


async def serialize_users(
    db: AsyncSession,
    users: list[User],
) -> list[dict[str, Any]]:
    if not users:
        return []

    user_ids = [user.id for user in users]

    membership_result = await db.execute(
        select(DepartmentMembership, Department)
        .join(Department, Department.id == DepartmentMembership.department_id)
        .where(
            and_(
                DepartmentMembership.user_id.in_(user_ids),
                DepartmentMembership.status == "active",
                Department.status == "active",
            )
        )
        .order_by(
            DepartmentMembership.is_primary.desc(),
            Department.name.asc(),
            DepartmentMembership.id.asc(),
        )
    )
    membership_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for membership, department in membership_result.all():
        membership_map[membership.user_id].append(serialize_membership_row(membership, department))

    managed_result = await db.execute(
        select(Department)
        .where(
            and_(
                Department.manager_user_id.in_(user_ids),
                Department.status == "active",
            )
        )
        .order_by(Department.name.asc())
    )
    managed_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for department in managed_result.scalars().all():
        managed_map[department.manager_user_id].append(
            {"id": department.id, "name": department.name, "code": department.code}
        )

    return [
        build_user_row(
            user=user,
            memberships=membership_map.get(user.id, []),
            managed_departments=managed_map.get(user.id, []),
        )
        for user in users
    ]


async def serialize_single_user(
    db: AsyncSession,
    user: User,
) -> dict[str, Any]:
    items = await serialize_users(db, [user])
    return items[0]


async def get_managed_departments_for_user(
    db: AsyncSession,
    user_id: int,
) -> list[Department]:
    result = await db.execute(
        select(Department)
        .where(
            and_(
                Department.manager_user_id == user_id,
                Department.status == "active",
            )
        )
        .order_by(Department.name.asc())
    )
    return list(result.scalars().all())


@router.get(
    "/users",
    summary="用户列表",
    description="平台管理员查看用户列表，并按关键字、部门、状态筛选。 List users for platform admins with filters.",
)
async def list_users(
    keyword: str | None = Query(default=None),
    department_id: int | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_platform_admin_access(current_user)

    conditions = []
    stmt = select(User)

    if keyword:
        normalized_keyword = f"%{keyword.strip().lower()}%"
        if normalized_keyword != "%%":
            conditions.append(
                or_(
                    func.lower(User.email).like(normalized_keyword),
                    func.lower(User.username).like(normalized_keyword),
                )
            )

    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))

    if department_id is not None:
        stmt = stmt.join(
            DepartmentMembership,
            and_(
                DepartmentMembership.user_id == User.id,
                DepartmentMembership.status == "active",
            ),
        )
        conditions.append(DepartmentMembership.department_id == department_id)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.distinct().order_by(User.created_at.desc(), User.id.desc())
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    return {
        "items": await serialize_users(db, users),
        "count": len(users),
    }


@router.patch(
    "/users/{user_id}/status",
    summary="更新用户状态",
    description="平台管理员启用或禁用用户。 Enable or disable a user as a platform admin.",
)
async def update_user_status(
    user_id: int,
    request: UserStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_platform_admin_access(current_user)

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_user.id and not request.is_active:
        raise HTTPException(status_code=400, detail="不能禁用当前登录账号")

    if not request.is_active:
        managed_departments = await get_managed_departments_for_user(db, user.id)
        if managed_departments:
            department_names = "、".join(department.name for department in managed_departments)
            raise HTTPException(
                status_code=400,
                detail=f"该用户仍是以下部门负责人，请先转交负责人：{department_names}",
            )

    user.is_active = request.is_active
    await db.commit()
    await db.refresh(user)

    return {
        "status": "success",
        "message": "用户状态已更新",
        "user": await serialize_single_user(db, user),
    }


@router.put(
    "/users/{user_id}/memberships",
    summary="更新用户部门归属",
    description="平台管理员维护用户的主部门与协作部门。 Replace a user's active department memberships.",
)
async def replace_user_memberships(
    user_id: int,
    request: UserMembershipUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_platform_admin_access(current_user)

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    normalized_items: list[UserMembershipItem] = []
    seen_department_ids: set[int] = set()
    for item in request.memberships:
        if item.department_id in seen_department_ids:
            raise HTTPException(status_code=400, detail="提交的部门归属中存在重复部门")
        seen_department_ids.add(item.department_id)
        normalized_items.append(item)

    if len(normalized_items) == 1 and not normalized_items[0].is_primary:
        normalized_items[0].is_primary = True

    if normalized_items:
        primary_count = sum(1 for item in normalized_items if item.is_primary)
        if primary_count != 1:
            raise HTTPException(status_code=400, detail="有部门归属时必须且只能指定一个主部门")

    requested_department_ids = [item.department_id for item in normalized_items]

    departments_by_id: dict[int, Department] = {}
    if requested_department_ids:
        department_result = await db.execute(
            select(Department).where(
                and_(
                    Department.id.in_(requested_department_ids),
                    Department.status == "active",
                )
            )
        )
        departments = list(department_result.scalars().all())
        departments_by_id = {department.id: department for department in departments}
        if len(departments_by_id) != len(requested_department_ids):
            raise HTTPException(status_code=404, detail="提交的部门中存在无效或已停用的部门")

    managed_departments = await get_managed_departments_for_user(db, user.id)
    requested_department_id_set = set(requested_department_ids)
    missing_managed_departments = [
        department for department in managed_departments if department.id not in requested_department_id_set
    ]
    if missing_managed_departments:
        department_names = "、".join(department.name for department in missing_managed_departments)
        raise HTTPException(
            status_code=400,
            detail=f"该用户仍是以下部门负责人，请先转交负责人：{department_names}",
        )

    active_membership_result = await db.execute(
        select(DepartmentMembership).where(
            and_(
                DepartmentMembership.user_id == user.id,
                DepartmentMembership.status == "active",
            )
        )
    )
    active_memberships = list(active_membership_result.scalars().all())
    active_membership_map = {
        membership.department_id: membership for membership in active_memberships
    }

    for membership in active_memberships:
        if membership.department_id not in requested_department_id_set:
            membership.status = "inactive"
            membership.is_primary = False

    for item in normalized_items:
        membership = active_membership_map.get(item.department_id)
        if membership is None:
            membership = DepartmentMembership(
                user_id=user.id,
                department_id=item.department_id,
                membership_type="primary" if item.is_primary else "secondary",
                is_primary=item.is_primary,
                status="active",
                approved_by=current_user.id,
            )
            db.add(membership)
        else:
            membership.membership_type = "primary" if item.is_primary else "secondary"
            membership.is_primary = item.is_primary
            membership.status = "active"
            membership.approved_by = current_user.id

    await db.commit()
    await db.refresh(user)

    return {
        "status": "success",
        "message": "用户部门归属已更新",
        "user": await serialize_single_user(db, user),
    }
