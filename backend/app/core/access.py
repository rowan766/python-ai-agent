from collections import defaultdict, deque

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import is_platform_admin
from app.models.department import Department, DepartmentMembership
from app.models.knowledge import KnowledgeBase, KnowledgeBaseShare
from app.models.user import User


async def get_active_member_department_ids(db: AsyncSession, user_id: int) -> list[int]:
    result = await db.execute(
        select(DepartmentMembership.department_id).where(
            and_(
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.status == "active",
            )
        )
    )
    return list(result.scalars().all())


async def get_managed_department_ids(db: AsyncSession, user_id: int) -> list[int]:
    result = await db.execute(
        select(Department.id).where(
            and_(Department.manager_user_id == user_id, Department.status == "active")
        )
    )
    return list(result.scalars().all())


def expand_department_descendants(
    departments: list[Department],
    root_ids: list[int],
) -> list[int]:
    if not root_ids:
        return []

    children_map: dict[int | None, list[int]] = defaultdict(list)
    for department in departments:
        children_map[department.parent_id].append(department.id)

    visited: set[int] = set()
    queue = deque(root_ids)

    while queue:
        department_id = queue.popleft()
        if department_id in visited:
            continue
        visited.add(department_id)
        for child_id in children_map.get(department_id, []):
            queue.append(child_id)

    return sorted(visited)


async def get_accessible_department_ids(db: AsyncSession, current_user: User) -> list[int]:
    departments_result = await db.execute(
        select(Department).where(Department.status == "active").order_by(Department.id.asc())
    )
    departments = list(departments_result.scalars().all())

    if is_platform_admin(current_user):
        return [department.id for department in departments]

    member_department_ids = await get_active_member_department_ids(db, current_user.id)
    managed_department_ids = await get_managed_department_ids(db, current_user.id)
    managed_scope_ids = expand_department_descendants(departments, managed_department_ids)

    return sorted(set(member_department_ids + managed_scope_ids))


async def can_manage_department(
    db: AsyncSession,
    current_user: User,
    department_id: int,
) -> bool:
    if is_platform_admin(current_user):
        return True

    managed_department_ids = await get_managed_department_ids(db, current_user.id)
    if not managed_department_ids:
        return False

    departments_result = await db.execute(
        select(Department).where(Department.status == "active").order_by(Department.id.asc())
    )
    departments = list(departments_result.scalars().all())
    return department_id in expand_department_descendants(departments, managed_department_ids)


async def get_accessible_knowledge_base_ids(db: AsyncSession, current_user: User) -> list[int]:
    if is_platform_admin(current_user):
        result = await db.execute(
            select(KnowledgeBase.id).where(KnowledgeBase.status == "active").order_by(KnowledgeBase.id.asc())
        )
        return list(result.scalars().all())

    accessible_department_ids = await get_accessible_department_ids(db, current_user)

    visibility_conditions = [KnowledgeBase.visibility_scope == "org_public"]
    if accessible_department_ids:
        visibility_conditions.extend(
            [
                KnowledgeBase.department_id.in_(accessible_department_ids),
                and_(
                    KnowledgeBase.visibility_scope == "department_shared",
                    KnowledgeBase.id.in_(
                        select(KnowledgeBaseShare.knowledge_base_id).where(
                            and_(
                                KnowledgeBaseShare.status == "active",
                                KnowledgeBaseShare.target_department_id.in_(accessible_department_ids),
                            )
                        )
                    ),
                ),
            ]
        )

    result = await db.execute(
        select(KnowledgeBase.id)
        .where(and_(KnowledgeBase.status == "active", or_(*visibility_conditions)))
        .order_by(KnowledgeBase.id.asc())
    )
    return list(dict.fromkeys(result.scalars().all()))
