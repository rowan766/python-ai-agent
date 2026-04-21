from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, text

from app.models import Department, Document, KnowledgeSpace, Role, RoleDepartment, User
from app.services.knowledge_space_permissions import build_space_access_clause, get_current_user_role_ids


def _collect_descendant_department_ids(db, root_department_ids: list[int]) -> set[int]:
    roots = [d for d in root_department_ids if d]
    if not roots:
        return set()

    # 用单条递归 CTE 替代逐层循环查询
    placeholders = ", ".join(str(i) for i in roots)
    result = db.execute(
        text(f"""
            WITH RECURSIVE dept_tree AS (
                SELECT id FROM sys_department WHERE id IN ({placeholders})
                UNION ALL
                SELECT d.id FROM sys_department d
                INNER JOIN dept_tree dt ON d.parent_id = dt.id
            )
            SELECT id FROM dept_tree
        """)
    )
    return {row[0] for row in result}


def _build_legacy_document_permission_clause(db, current_user, *, action: str = "read") -> object | None:
    role_ids = get_current_user_role_ids(db, current_user)
    if action in {"write", "manage", "share"}:
        if not role_ids:
            return Document.user_id == current_user.id
        roles = db.scalars(select(Role).where(Role.id.in_(role_ids), Role.status == 1)).all()
        if any(role.data_scope == 1 for role in roles):
            return None
        return Document.user_id == current_user.id

    if not role_ids:
        return Document.user_id == current_user.id

    roles = db.scalars(select(Role).where(Role.id.in_(role_ids), Role.status == 1)).all()
    if not roles:
        return Document.user_id == current_user.id

    if any(role.data_scope == 1 for role in roles):
        return None

    clauses: list[object] = []

    if any(role.data_scope == 4 for role in roles):
        clauses.append(Document.user_id == current_user.id)

    if current_user.department_id:
        if any(role.data_scope == 3 for role in roles):
            clauses.append(
                Document.user_id.in_(
                    select(User.id).where(User.department_id == current_user.department_id)
                )
            )

        if any(role.data_scope == 2 for role in roles):
            department_ids = sorted(_collect_descendant_department_ids(db, [current_user.department_id]))
            if department_ids:
                clauses.append(
                    Document.user_id.in_(
                        select(User.id).where(User.department_id.in_(department_ids))
                    )
                )

    custom_role_ids = [role.id for role in roles if role.data_scope == 5]
    if custom_role_ids:
        assigned_department_ids = db.scalars(
            select(RoleDepartment.department_id).where(RoleDepartment.role_id.in_(custom_role_ids))
        ).all()
        custom_department_ids = sorted(_collect_descendant_department_ids(db, assigned_department_ids))
        if custom_department_ids:
            clauses.append(
                Document.user_id.in_(
                    select(User.id).where(User.department_id.in_(custom_department_ids))
                )
            )

    if not clauses:
        return Document.user_id == current_user.id
    return or_(*clauses)


def build_document_permission_clause(db, current_user, *, action: str = "read") -> object | None:
    legacy_clause = _build_legacy_document_permission_clause(db, current_user, action=action)
    if legacy_clause is None:
        return None

    clauses: list[object] = [and_(Document.space_id.is_(None), legacy_clause)]
    space_access_clause = build_space_access_clause(db, current_user, action=action)
    if space_access_clause is None:
        return None
    clauses.append(
        and_(
            Document.space_id.is_not(None),
            Document.space_id.in_(select(KnowledgeSpace.id).where(space_access_clause)),
        )
    )
    return or_(*clauses)


def get_accessible_document_ids(
    db,
    current_user,
    *,
    action: str = "read",
    document_id: int | None = None,
    document_ids: list[int] | None = None,
    space_id: int | None = None,
    space_ids: list[int] | None = None,
) -> list[int]:
    statement = select(Document.id)
    permission_clause = build_document_permission_clause(db, current_user, action=action)
    if permission_clause is not None:
        statement = statement.where(permission_clause)

    if document_id is not None:
        statement = statement.where(Document.id == document_id)
    elif document_ids is not None and len(document_ids) > 0:
        statement = statement.where(Document.id.in_(document_ids))

    if space_id is not None:
        statement = statement.where(Document.space_id == space_id)
    elif space_ids is not None and len(space_ids) > 0:
        statement = statement.where(Document.space_id.in_(space_ids))

    return list(db.scalars(statement).all())


def get_document_or_404(db, current_user, document_id: int, *, action: str = "read") -> Document:
    statement = select(Document).where(Document.id == document_id)
    permission_clause = build_document_permission_clause(db, current_user, action=action)
    if permission_clause is not None:
        statement = statement.where(permission_clause)
    document = db.scalar(statement)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    return document
