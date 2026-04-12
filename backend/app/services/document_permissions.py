from __future__ import annotations

from sqlalchemy import or_, select

from app.models import Department, Document, Role, RoleDepartment, User, UserRole


def _collect_descendant_department_ids(db, root_department_ids: list[int]) -> set[int]:
    pending = {department_id for department_id in root_department_ids if department_id}
    collected: set[int] = set()

    while pending:
        current_batch = pending - collected
        if not current_batch:
            break
        collected.update(current_batch)
        child_ids = set(
            db.scalars(select(Department.id).where(Department.parent_id.in_(sorted(current_batch)))).all()
        )
        pending.update(child_ids)

    return collected


def build_document_permission_clause(db, current_user) -> object | None:
    role_ids = db.scalars(select(UserRole.role_id).where(UserRole.user_id == current_user.id)).all()
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


def get_accessible_document_ids(db, current_user, *, document_id: int | None = None) -> list[int]:
    statement = select(Document.id)
    permission_clause = build_document_permission_clause(db, current_user)
    if permission_clause is not None:
        statement = statement.where(permission_clause)
    if document_id is not None:
        statement = statement.where(Document.id == document_id)
    return list(db.scalars(statement).all())
