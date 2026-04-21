from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, text

from app.models import KnowledgeSpace, KnowledgeSpaceMember, KnowledgeSpaceShare, Role, UserRole


SPACE_ROLE_ACTIONS: dict[str, set[str]] = {
    "owner": {"read", "write", "manage", "share"},
    "manager": {"read", "write", "manage", "share"},
    "editor": {"read", "write"},
    "viewer": {"read"},
}

PERMISSION_LEVEL_ORDER = {
    "read": 1,
    "write": 2,
    "manage": 3,
    "share": 4,
}

VALID_SPACE_ROLES = set(SPACE_ROLE_ACTIONS.keys())
VALID_PERMISSION_LEVELS = set(PERMISSION_LEVEL_ORDER.keys())
VALID_SHARE_TARGET_TYPES = {"department", "role", "user"}
VALID_VISIBILITY_MODES = {"private", "department", "department_tree", "shared", "all"}
DEFAULT_SPACE_NAME = "默认知识空间"


def get_current_user_role_ids(db, current_user) -> list[int]:
    return list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == current_user.id)).all())


def is_platform_super_admin(db, current_user) -> bool:
    role_ids = get_current_user_role_ids(db, current_user)
    if not role_ids:
        return False
    roles = db.scalars(select(Role).where(Role.id.in_(role_ids), Role.status == 1)).all()
    return any(role.data_scope == 1 for role in roles)


def _permission_allows(granted: str, required: str) -> bool:
    return PERMISSION_LEVEL_ORDER.get(granted, 0) >= PERMISSION_LEVEL_ORDER.get(required, 0)


def _allowed_space_roles(required_action: str) -> list[str]:
    return [role for role, actions in SPACE_ROLE_ACTIONS.items() if required_action in actions]


def _allowed_share_levels(required_action: str) -> list[str]:
    return [level for level in PERMISSION_LEVEL_ORDER if _permission_allows(level, required_action)]


def build_space_access_clause(db, current_user, *, action: str = "read") -> object | None:
    if is_platform_super_admin(db, current_user):
        return None

    clauses: list[object] = [KnowledgeSpace.created_by == current_user.id]

    allowed_member_roles = _allowed_space_roles(action)
    if allowed_member_roles:
        clauses.append(
            KnowledgeSpace.id.in_(
                select(KnowledgeSpaceMember.space_id).where(
                    KnowledgeSpaceMember.user_id == current_user.id,
                    KnowledgeSpaceMember.space_role.in_(allowed_member_roles),
                )
            )
        )

    allowed_share_levels = _allowed_share_levels(action)
    share_target_clauses: list[object] = [
        and_(
            KnowledgeSpaceShare.target_type == "user",
            KnowledgeSpaceShare.target_id == current_user.id,
        )
    ]
    role_ids = get_current_user_role_ids(db, current_user)
    if role_ids:
        share_target_clauses.append(
            and_(
                KnowledgeSpaceShare.target_type == "role",
                KnowledgeSpaceShare.target_id.in_(role_ids),
            )
        )
    if current_user.department_id:
        share_target_clauses.append(
            and_(
                KnowledgeSpaceShare.target_type == "department",
                KnowledgeSpaceShare.target_id == current_user.department_id,
            )
        )

    if allowed_share_levels and share_target_clauses:
        clauses.append(
            KnowledgeSpace.id.in_(
                select(KnowledgeSpaceShare.space_id).where(
                    KnowledgeSpaceShare.permission_level.in_(allowed_share_levels),
                    or_(*share_target_clauses),
                )
            )
        )

    if action == "read":
        # 全体成员可见：任何登录用户均可读取
        clauses.append(KnowledgeSpace.visibility_mode == "all")

        if current_user.department_id:
            # 同部门可见：归属部门与当前用户部门精确匹配
            clauses.append(
                and_(
                    KnowledgeSpace.visibility_mode == "department",
                    KnowledgeSpace.owner_department_id == current_user.department_id,
                )
            )
            # 同部门及下属部门可见：用递归 CTE 查出归属部门的所有上级，
            # 只要当前用户的部门在某空间归属部门的子树内，就放行
            ancestor_ids_result = db.execute(
                text("""
                    WITH RECURSIVE dept_ancestors AS (
                        SELECT id, parent_id FROM sys_department WHERE id = :dept_id
                        UNION ALL
                        SELECT d.id, d.parent_id FROM sys_department d
                        INNER JOIN dept_ancestors da ON d.id = da.parent_id
                    )
                    SELECT id FROM dept_ancestors
                """),
                {"dept_id": current_user.department_id},
            )
            ancestor_ids = [row[0] for row in ancestor_ids_result]
            if ancestor_ids:
                clauses.append(
                    and_(
                        KnowledgeSpace.visibility_mode == "department_tree",
                        KnowledgeSpace.owner_department_id.in_(ancestor_ids),
                    )
                )

    return or_(*clauses)


def get_accessible_space_ids(db, current_user, *, action: str = "read") -> list[int]:
    statement = select(KnowledgeSpace.id)
    access_clause = build_space_access_clause(db, current_user, action=action)
    if access_clause is not None:
        statement = statement.where(access_clause)
    return list(db.scalars(statement).all())


def get_knowledge_space_or_404(db, current_user, space_id: int, *, action: str = "read") -> KnowledgeSpace:
    statement = select(KnowledgeSpace).where(KnowledgeSpace.id == space_id)
    access_clause = build_space_access_clause(db, current_user, action=action)
    if access_clause is not None:
        statement = statement.where(access_clause)
    space = db.scalar(statement)
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识空间不存在")
    return space


def normalize_space_role(space_role: str | None) -> str:
    role = (space_role or "viewer").strip().lower()
    if role not in VALID_SPACE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="spaceRole 仅支持 owner、manager、editor、viewer",
        )
    return role


def normalize_permission_level(permission_level: str | None) -> str:
    level = (permission_level or "read").strip().lower()
    if level not in VALID_PERMISSION_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="permissionLevel 仅支持 read、write、manage、share",
        )
    return level


def normalize_share_target_type(target_type: str | None) -> str:
    normalized = (target_type or "").strip().lower()
    if normalized not in VALID_SHARE_TARGET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="targetType 仅支持 department、role、user",
        )
    return normalized


def ensure_space_has_owner(db, space_id: int, *, excluding_member_id: int | None = None) -> None:
    statement = select(KnowledgeSpaceMember.id).where(
        KnowledgeSpaceMember.space_id == space_id,
        KnowledgeSpaceMember.space_role == "owner",
    )
    if excluding_member_id is not None:
        statement = statement.where(KnowledgeSpaceMember.id != excluding_member_id)
    existing_owner = db.scalar(statement.limit(1))
    if not existing_owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="知识空间至少需要保留一个 owner")


def ensure_default_knowledge_space(db, current_user) -> KnowledgeSpace:
    existing = db.scalar(
        select(KnowledgeSpace)
        .where(
            KnowledgeSpace.created_by == current_user.id,
            KnowledgeSpace.name == DEFAULT_SPACE_NAME,
        )
        .order_by(KnowledgeSpace.id.asc())
    )
    if existing:
        return existing

    space = KnowledgeSpace(
        name=DEFAULT_SPACE_NAME,
        description="系统自动创建的默认知识空间",
        status=1,
        created_by=current_user.id,
        owner_department_id=current_user.department_id,
        visibility_mode="private",
    )
    db.add(space)
    db.flush()
    db.add(
        KnowledgeSpaceMember(
            space_id=space.id,
            user_id=current_user.id,
            space_role="owner",
        )
    )
    db.flush()
    return space
