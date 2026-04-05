from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, is_platform_admin
from app.core.access import can_manage_department, expand_department_descendants
from app.core.database import get_db
from app.models.department import Department, DepartmentJoinRequest, DepartmentMembership
from app.models.knowledge import KnowledgeBase, KnowledgeDocument
from app.models.user import User

router = APIRouter()


class DepartmentBootstrapRequest(BaseModel):
    code: str
    name: str
    full_name: str | None = None


class DepartmentJoinCreateRequest(BaseModel):
    target_department_id: int
    requested_role_code: str | None = None
    reason: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target_department_id": 1,
                "requested_role_code": "department_member",
                "reason": "负责接入部门知识库并参与文档治理。",
            }
        }
    )


class DepartmentJoinDecisionRequest(BaseModel):
    review_comment: str | None = None


class DepartmentCreateRequest(BaseModel):
    parent_id: int | None = None
    code: str
    name: str
    full_name: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "parent_id": 1,
                "code": "dept-rd-platform",
                "name": "平台研发部",
                "full_name": "研发中心 / 平台研发部",
            }
        }
    )


class DepartmentUpdateRequest(BaseModel):
    name: str | None = None
    full_name: str | None = None
    status: str | None = None


class DepartmentManagerUpdateRequest(BaseModel):
    manager_user_id: int


class DepartmentParentUpdateRequest(BaseModel):
    parent_id: int | None = None


def build_department_tree_rows(departments: list[Department]) -> list[dict[str, Any]]:
    nodes: dict[int, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    for department in departments:
        nodes[department.id] = {
            "id": department.id,
            "parent_id": department.parent_id,
            "code": department.code,
            "name": department.name,
            "full_name": department.full_name or department.name,
            "manager_user_id": department.manager_user_id,
            "status": department.status,
            "children": [],
        }

    for department in departments:
        node = nodes[department.id]
        if department.parent_id and department.parent_id in nodes:
            nodes[department.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


async def serialize_membership_summary(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    result = await db.execute(
        select(DepartmentMembership, Department)
        .join(Department, Department.id == DepartmentMembership.department_id)
        .where(
            and_(
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.status == "active",
            )
        )
        .order_by(DepartmentMembership.is_primary.desc(), Department.id.asc())
    )
    rows = result.all()
    return [
        {
            "id": membership.id,
            "department_id": department.id,
            "department_name": department.name,
            "department_code": department.code,
            "membership_type": membership.membership_type,
            "is_primary": membership.is_primary,
            "status": membership.status,
        }
        for membership, department in rows
    ]


async def ensure_department_manager_access(
    db: AsyncSession,
    department_id: int,
    current_user: User,
) -> Department:
    department = await db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")

    if department.manager_user_id != current_user.id and not is_platform_admin(current_user):
        raise HTTPException(status_code=403, detail="你没有审批该部门申请的权限")

    return department


async def ensure_department_creation_access(
    db: AsyncSession,
    parent_id: int | None,
    current_user: User,
) -> Department | None:
    if parent_id is None:
        if is_platform_admin(current_user):
            return None
        raise HTTPException(status_code=403, detail="仅平台管理员可以创建新的根部门")

    parent_department = await db.get(Department, parent_id)
    if not parent_department or parent_department.status != "active":
        raise HTTPException(status_code=404, detail="上级部门不存在或不可用")

    if not await can_manage_department(db, current_user, parent_department.id):
        raise HTTPException(status_code=403, detail="仅上级部门负责人或平台管理员可以新增子部门")

    return parent_department


async def get_all_active_departments(db: AsyncSession) -> list[Department]:
    result = await db.execute(
        select(Department).where(Department.status == "active").order_by(Department.id.asc())
    )
    return list(result.scalars().all())


def get_department_descendant_ids(
    departments: list[Department],
    department_id: int,
) -> list[int]:
    descendant_ids = expand_department_descendants(departments, [department_id])
    return [item for item in descendant_ids if item != department_id]


@router.get(
    "/departments/tree",
    summary="部门树 Department Tree",
    description="获取当前系统中的部门树结构。 Return the department tree in the system.",
)
async def get_department_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    departments = await get_all_active_departments(db)
    return {
        "items": build_department_tree_rows(departments),
        "count": len(departments),
    }


@router.post(
    "/departments/bootstrap",
    summary="初始化首个部门 Bootstrap First Department",
    description="当系统中还没有任何部门时，创建首个根部门并将当前用户设为负责人。 Bootstrap the first department when the system is empty.",
)
async def bootstrap_first_department(
    request: DepartmentBootstrapRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_result = await db.execute(select(Department.id).limit(1))
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="系统已存在部门，不能重复初始化")

    code = request.code.strip()
    name = request.name.strip()
    full_name = (request.full_name or "").strip() or name
    if not code or not name:
        raise HTTPException(status_code=400, detail="部门编码和名称不能为空")

    department = Department(
        code=code,
        name=name,
        full_name=full_name,
        manager_user_id=current_user.id,
    )
    db.add(department)
    await db.flush()

    membership = DepartmentMembership(
        user_id=current_user.id,
        department_id=department.id,
        membership_type="primary",
        is_primary=True,
        status="active",
        approved_by=current_user.id,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(department)

    return {
        "status": "success",
        "message": "首个部门初始化成功",
        "department": {
            "id": department.id,
            "code": department.code,
            "name": department.name,
            "full_name": department.full_name,
            "manager_user_id": department.manager_user_id,
        },
    }


@router.post(
    "/departments",
    summary="创建部门 Create Department",
    description="创建新的部门节点，用于维护组织树。 Create a department node for organization tree management.",
)
async def create_department(
    request: DepartmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent_department = await ensure_department_creation_access(
        db=db,
        parent_id=request.parent_id,
        current_user=current_user,
    )

    code = request.code.strip()
    name = request.name.strip()
    full_name = (request.full_name or "").strip() or name

    if not code or not name:
        raise HTTPException(status_code=400, detail="部门编码和名称不能为空")

    existing_code_result = await db.execute(select(Department.id).where(Department.code == code))
    if existing_code_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="该部门编码已存在")

    department = Department(
        parent_id=parent_department.id if parent_department else None,
        code=code,
        name=name,
        full_name=full_name,
        manager_user_id=current_user.id,
        status="active",
    )
    db.add(department)
    await db.flush()

    existing_membership_result = await db.execute(
        select(DepartmentMembership).where(
            and_(
                DepartmentMembership.user_id == current_user.id,
                DepartmentMembership.department_id == department.id,
                DepartmentMembership.status == "active",
            )
        )
    )
    if existing_membership_result.scalar_one_or_none() is None:
        primary_membership_result = await db.execute(
            select(DepartmentMembership.id).where(
                and_(
                    DepartmentMembership.user_id == current_user.id,
                    DepartmentMembership.status == "active",
                    DepartmentMembership.is_primary.is_(True),
                )
            )
        )
        has_primary_membership = primary_membership_result.scalar_one_or_none() is not None
        db.add(
            DepartmentMembership(
                user_id=current_user.id,
                department_id=department.id,
                membership_type="secondary" if has_primary_membership else "primary",
                is_primary=not has_primary_membership,
                status="active",
                approved_by=current_user.id,
            )
        )

    await db.commit()
    await db.refresh(department)

    return {
        "status": "success",
        "message": "部门创建成功",
        "department": {
            "id": department.id,
            "parent_id": department.parent_id,
            "code": department.code,
            "name": department.name,
            "full_name": department.full_name,
            "manager_user_id": department.manager_user_id,
            "status": department.status,
        },
    }


@router.patch(
    "/departments/{department_id}",
    summary="更新部门 Update Department",
    description="更新部门的基本信息和状态。 Update basic department information and status.",
)
async def update_department(
    department_id: int,
    request: DepartmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    department = await ensure_department_manager_access(
        db=db,
        department_id=department_id,
        current_user=current_user,
    )

    if request.name is not None:
        normalized_name = request.name.strip()
        if not normalized_name:
            raise HTTPException(status_code=400, detail="部门名称不能为空")
        department.name = normalized_name

    if request.full_name is not None:
        normalized_full_name = request.full_name.strip()
        department.full_name = normalized_full_name or department.name

    if request.status is not None:
        normalized_status = request.status.strip()
        if normalized_status not in {"active", "inactive"}:
            raise HTTPException(status_code=400, detail="部门状态仅支持 active 或 inactive")
        department.status = normalized_status

    await db.commit()
    await db.refresh(department)

    return {
        "status": "success",
        "message": "部门信息已更新",
        "department": {
            "id": department.id,
            "parent_id": department.parent_id,
            "code": department.code,
            "name": department.name,
            "full_name": department.full_name,
            "manager_user_id": department.manager_user_id,
            "status": department.status,
        },
    }


@router.get(
    "/departments/{department_id}/members",
    summary="部门成员 Department Members",
    description="查看指定部门的有效成员列表。 List active members of a department.",
)
async def get_department_members(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ensure_department_manager_access(
        db=db,
        department_id=department_id,
        current_user=current_user,
    )

    result = await db.execute(
        select(DepartmentMembership, User)
        .join(User, User.id == DepartmentMembership.user_id)
        .where(
            and_(
                DepartmentMembership.department_id == department_id,
                DepartmentMembership.status == "active",
                User.is_active.is_(True),
            )
        )
        .order_by(DepartmentMembership.is_primary.desc(), User.username.asc())
    )

    items = [
        {
            "membership_id": membership.id,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "membership_type": membership.membership_type,
            "is_primary": membership.is_primary,
            "status": membership.status,
        }
        for membership, user in result.all()
    ]
    return {"items": items, "count": len(items)}


@router.get(
    "/departments/{department_id}/impact",
    summary="部门影响评估 Department Impact",
    description="查看部门停用或调整前的影响范围。 Preview the impact of changing or disabling a department.",
)
async def get_department_impact(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ensure_department_manager_access(
        db=db,
        department_id=department_id,
        current_user=current_user,
    )

    departments = await get_all_active_departments(db)
    descendant_ids = get_department_descendant_ids(departments, department_id)

    member_count_result = await db.execute(
        select(func.count(DepartmentMembership.id)).where(
            and_(
                DepartmentMembership.department_id == department_id,
                DepartmentMembership.status == "active",
            )
        )
    )
    knowledge_base_count_result = await db.execute(
        select(func.count(KnowledgeBase.id)).where(
            and_(
                KnowledgeBase.department_id == department_id,
                KnowledgeBase.status == "active",
            )
        )
    )
    document_count_result = await db.execute(
        select(func.count(KnowledgeDocument.id)).where(
            and_(
                KnowledgeDocument.department_id == department_id,
                KnowledgeDocument.status == "active",
            )
        )
    )

    return {
        "department_id": department_id,
        "child_department_count": len(descendant_ids),
        "active_member_count": member_count_result.scalar_one(),
        "knowledge_base_count": knowledge_base_count_result.scalar_one(),
        "document_count": document_count_result.scalar_one(),
    }


@router.patch(
    "/departments/{department_id}/manager",
    summary="设置部门负责人 Assign Department Manager",
    description="为部门指定负责人，负责人必须是该部门的有效成员。 Assign a manager for the department.",
)
async def update_department_manager(
    department_id: int,
    request: DepartmentManagerUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    department = await ensure_department_manager_access(
        db=db,
        department_id=department_id,
        current_user=current_user,
    )

    user_result = await db.execute(select(User).where(User.id == request.manager_user_id))
    manager_user = user_result.scalar_one_or_none()
    if not manager_user or not manager_user.is_active:
        raise HTTPException(status_code=404, detail="目标负责人不存在或不可用")

    membership_result = await db.execute(
        select(DepartmentMembership).where(
            and_(
                DepartmentMembership.department_id == department_id,
                DepartmentMembership.user_id == request.manager_user_id,
                DepartmentMembership.status == "active",
            )
        )
    )
    if membership_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="目标负责人必须是该部门的有效成员")

    department.manager_user_id = manager_user.id
    await db.commit()
    await db.refresh(department)

    return {
        "status": "success",
        "message": "部门负责人已更新",
        "department": {
            "id": department.id,
            "manager_user_id": department.manager_user_id,
        },
    }


@router.patch(
    "/departments/{department_id}/parent",
    summary="调整部门层级 Move Department",
    description="调整部门在组织树中的上级节点。 Move a department under another parent department.",
)
async def update_department_parent(
    department_id: int,
    request: DepartmentParentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    department = await ensure_department_manager_access(
        db=db,
        department_id=department_id,
        current_user=current_user,
    )

    if request.parent_id == department.id:
        raise HTTPException(status_code=400, detail="部门不能把自己设为上级")

    departments = await get_all_active_departments(db)
    descendant_ids = get_department_descendant_ids(departments, department.id)
    if request.parent_id in descendant_ids:
        raise HTTPException(status_code=400, detail="不能把部门移动到自己的下级节点下")

    if request.parent_id is not None:
        await ensure_department_creation_access(
            db=db,
            parent_id=request.parent_id,
            current_user=current_user,
        )
    elif not is_platform_admin(current_user):
        raise HTTPException(status_code=403, detail="仅平台管理员可以把部门提升为根部门")

    department.parent_id = request.parent_id
    await db.commit()
    await db.refresh(department)

    return {
        "status": "success",
        "message": "部门层级已更新",
        "department": {
            "id": department.id,
            "parent_id": department.parent_id,
        },
    }


@router.post(
    "/department-requests",
    summary="申请加入部门 Create Department Join Request",
    description="当前用户发起加入部门申请。 Create a department join request for the current user.",
)
async def create_department_join_request(
    request: DepartmentJoinCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reason = request.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="申请理由不能为空")

    department = await db.get(Department, request.target_department_id)
    if not department or department.status != "active":
        raise HTTPException(status_code=404, detail="目标部门不存在或不可用")

    membership_result = await db.execute(
        select(DepartmentMembership).where(
            and_(
                DepartmentMembership.user_id == current_user.id,
                DepartmentMembership.department_id == request.target_department_id,
                DepartmentMembership.status == "active",
            )
        )
    )
    if membership_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="你已经属于该部门")

    pending_result = await db.execute(
        select(DepartmentJoinRequest).where(
            and_(
                DepartmentJoinRequest.user_id == current_user.id,
                DepartmentJoinRequest.target_department_id == request.target_department_id,
                DepartmentJoinRequest.status == "pending",
            )
        )
    )
    if pending_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="你已有一条待审批的申请")

    join_request = DepartmentJoinRequest(
        user_id=current_user.id,
        target_department_id=request.target_department_id,
        requested_role_code=request.requested_role_code,
        reason=reason,
        status="pending",
    )
    db.add(join_request)
    await db.commit()
    await db.refresh(join_request)

    return {
        "status": "success",
        "message": "加入部门申请已提交",
        "request": {
            "id": join_request.id,
            "target_department_id": join_request.target_department_id,
            "requested_role_code": join_request.requested_role_code,
            "reason": join_request.reason,
            "status": join_request.status,
            "submitted_at": join_request.submitted_at,
        },
    }


@router.get(
    "/department-requests/my",
    summary="我的部门申请 My Department Join Requests",
    description="查看当前用户发起的部门加入申请。 List department join requests created by the current user.",
)
async def get_my_department_join_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DepartmentJoinRequest, Department)
        .join(Department, Department.id == DepartmentJoinRequest.target_department_id)
        .where(DepartmentJoinRequest.user_id == current_user.id)
        .order_by(DepartmentJoinRequest.submitted_at.desc())
    )

    items = []
    for join_request, department in result.all():
        items.append(
            {
                "id": join_request.id,
                "target_department_id": department.id,
                "target_department_name": department.name,
                "requested_role_code": join_request.requested_role_code,
                "reason": join_request.reason,
                "status": join_request.status,
                "review_comment": join_request.review_comment,
                "submitted_at": join_request.submitted_at,
                "reviewed_at": join_request.reviewed_at,
            }
        )

    return {"items": items, "count": len(items)}


@router.get(
    "/department-requests/pending",
    summary="待审批部门申请 Pending Department Join Requests",
    description="查看当前用户可审批的部门加入申请。 List pending department join requests reviewable by the current user.",
)
async def get_pending_department_join_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    managed_department_ids_result = await db.execute(
        select(Department.id).where(Department.manager_user_id == current_user.id)
    )
    managed_department_ids = list(managed_department_ids_result.scalars().all())

    conditions = [DepartmentJoinRequest.status == "pending"]
    if managed_department_ids:
        conditions.append(DepartmentJoinRequest.target_department_id.in_(managed_department_ids))

    if is_platform_admin(current_user):
        where_clause = DepartmentJoinRequest.status == "pending"
    elif managed_department_ids:
        where_clause = and_(*conditions)
    else:
        return {"items": [], "count": 0}

    result = await db.execute(
        select(DepartmentJoinRequest, Department, User)
        .join(Department, Department.id == DepartmentJoinRequest.target_department_id)
        .join(User, User.id == DepartmentJoinRequest.user_id)
        .where(where_clause)
        .order_by(DepartmentJoinRequest.submitted_at.asc())
    )

    items = []
    for join_request, department, applicant in result.all():
        items.append(
            {
                "id": join_request.id,
                "applicant_user_id": applicant.id,
                "applicant_email": applicant.email,
                "applicant_username": applicant.username,
                "target_department_id": department.id,
                "target_department_name": department.name,
                "requested_role_code": join_request.requested_role_code,
                "reason": join_request.reason,
                "status": join_request.status,
                "submitted_at": join_request.submitted_at,
            }
        )

    return {"items": items, "count": len(items)}


@router.post(
    "/department-requests/{request_id}/approve",
    summary="通过部门申请 Approve Department Join Request",
    description="审批通过部门加入申请，并创建有效成员关系。 Approve a department join request and create the membership.",
)
async def approve_department_join_request(
    request_id: int,
    request: DepartmentJoinDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DepartmentJoinRequest).where(DepartmentJoinRequest.id == request_id)
    )
    join_request = result.scalar_one_or_none()
    if not join_request:
        raise HTTPException(status_code=404, detail="申请不存在")
    if join_request.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理，不能重复审批")

    department = await ensure_department_manager_access(
        db=db,
        department_id=join_request.target_department_id,
        current_user=current_user,
    )

    existing_membership_result = await db.execute(
        select(DepartmentMembership).where(
            and_(
                DepartmentMembership.user_id == join_request.user_id,
                DepartmentMembership.department_id == join_request.target_department_id,
                DepartmentMembership.status == "active",
            )
        )
    )
    if existing_membership_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户已属于该部门")

    primary_membership_result = await db.execute(
        select(DepartmentMembership).where(
            and_(
                DepartmentMembership.user_id == join_request.user_id,
                DepartmentMembership.status == "active",
                DepartmentMembership.is_primary.is_(True),
            )
        )
    )
    has_primary_membership = primary_membership_result.scalar_one_or_none() is not None

    membership = DepartmentMembership(
        user_id=join_request.user_id,
        department_id=join_request.target_department_id,
        membership_type="secondary" if has_primary_membership else "primary",
        is_primary=not has_primary_membership,
        status="active",
        approved_by=current_user.id,
    )
    db.add(membership)

    join_request.status = "approved"
    join_request.reviewer_user_id = current_user.id
    join_request.review_comment = (request.review_comment or "").strip() or "审批通过"
    join_request.reviewed_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",
        "message": f"已通过加入 {department.name} 的申请",
    }


@router.post(
    "/department-requests/{request_id}/reject",
    summary="驳回部门申请 Reject Department Join Request",
    description="驳回部门加入申请。 Reject a department join request.",
)
async def reject_department_join_request(
    request_id: int,
    request: DepartmentJoinDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DepartmentJoinRequest).where(DepartmentJoinRequest.id == request_id)
    )
    join_request = result.scalar_one_or_none()
    if not join_request:
        raise HTTPException(status_code=404, detail="申请不存在")
    if join_request.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理，不能重复审批")

    await ensure_department_manager_access(
        db=db,
        department_id=join_request.target_department_id,
        current_user=current_user,
    )

    join_request.status = "rejected"
    join_request.reviewer_user_id = current_user.id
    join_request.review_comment = (request.review_comment or "").strip() or "审批拒绝"
    join_request.reviewed_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "success",
        "message": "已驳回该部门申请",
    }
