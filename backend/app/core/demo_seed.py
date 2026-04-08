import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import and_, select

from app.core.auth import hash_password
from app.core.database import AsyncSessionLocal
from app.core.paths import UPLOAD_DIR
from app.models.department import Department, DepartmentJoinRequest, DepartmentMembership
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeBaseShare,
    KnowledgeBaseShareRequest,
    KnowledgeDocument,
)
from app.models.user import User

logger = logging.getLogger("uvicorn.error")

DEMO_PASSWORD = os.getenv("DEMO_SEED_PASSWORD", "Password123!")

DEMO_USERS = [
    {
        "email": "admin.demo@example.com",
        "username": "demo_admin",
        "password": DEMO_PASSWORD,
    },
    {
        "email": "lena.demo@example.com",
        "username": "demo_lena",
        "password": DEMO_PASSWORD,
    },
    {
        "email": "chen.demo@example.com",
        "username": "demo_chen",
        "password": DEMO_PASSWORD,
    },
    {
        "email": "maya.demo@example.com",
        "username": "demo_maya",
        "password": DEMO_PASSWORD,
    },
    {
        "email": "nora.demo@example.com",
        "username": "demo_nora",
        "password": DEMO_PASSWORD,
    },
    {
        "email": "jack.demo@example.com",
        "username": "demo_jack",
        "password": DEMO_PASSWORD,
    },
]

DEMO_DEPARTMENTS = [
    {
        "code": "dept-root",
        "name": "企业知识中心",
        "full_name": "企业知识中心",
        "parent_code": None,
        "manager_email": "admin.demo@example.com",
    },
    {
        "code": "dept-product",
        "name": "产品运营部",
        "full_name": "企业知识中心 / 产品运营部",
        "parent_code": "dept-root",
        "manager_email": "lena.demo@example.com",
    },
    {
        "code": "dept-rd",
        "name": "平台研发部",
        "full_name": "企业知识中心 / 平台研发部",
        "parent_code": "dept-root",
        "manager_email": "chen.demo@example.com",
    },
    {
        "code": "dept-delivery",
        "name": "交付服务部",
        "full_name": "企业知识中心 / 交付服务部",
        "parent_code": "dept-root",
        "manager_email": "maya.demo@example.com",
    },
]

DEMO_MEMBERSHIPS = [
    {
        "email": "admin.demo@example.com",
        "department_code": "dept-root",
        "membership_type": "primary",
        "is_primary": True,
        "approved_by": "admin.demo@example.com",
    },
    {
        "email": "lena.demo@example.com",
        "department_code": "dept-product",
        "membership_type": "primary",
        "is_primary": True,
        "approved_by": "admin.demo@example.com",
    },
    {
        "email": "chen.demo@example.com",
        "department_code": "dept-rd",
        "membership_type": "primary",
        "is_primary": True,
        "approved_by": "admin.demo@example.com",
    },
    {
        "email": "maya.demo@example.com",
        "department_code": "dept-delivery",
        "membership_type": "primary",
        "is_primary": True,
        "approved_by": "admin.demo@example.com",
    },
    {
        "email": "nora.demo@example.com",
        "department_code": "dept-product",
        "membership_type": "primary",
        "is_primary": True,
        "approved_by": "lena.demo@example.com",
    },
    {
        "email": "nora.demo@example.com",
        "department_code": "dept-rd",
        "membership_type": "secondary",
        "is_primary": False,
        "approved_by": "chen.demo@example.com",
    },
]

DEMO_KNOWLEDGE_BASES = [
    {
        "code": "company-handbook",
        "name": "企业协作手册",
        "description": "跨部门共享的流程说明、平台使用指引与组织协作规则。",
        "department_code": "dept-root",
        "created_by": "admin.demo@example.com",
        "visibility_scope": "org_public",
    },
    {
        "code": "product-playbook",
        "name": "产品运营作战室",
        "description": "版本节奏、活动复盘、需求共识和经营周会资料。",
        "department_code": "dept-product",
        "created_by": "lena.demo@example.com",
        "visibility_scope": "department_private",
    },
    {
        "code": "rd-standards",
        "name": "平台研发规范库",
        "description": "研发流程、上线规范、值班手册和接口协作标准。",
        "department_code": "dept-rd",
        "created_by": "chen.demo@example.com",
        "visibility_scope": "department_shared",
    },
    {
        "code": "delivery-sop",
        "name": "交付现场 SOP",
        "description": "项目交付现场问题处理、升级路径和客户沟通模板。",
        "department_code": "dept-delivery",
        "created_by": "maya.demo@example.com",
        "visibility_scope": "department_private",
    },
]

DEMO_DOCUMENTS = [
    {
        "knowledge_base_code": "company-handbook",
        "uploader_email": "admin.demo@example.com",
        "title": "企业知识平台使用手册",
        "filename": "enterprise-handbook.md",
        "visibility_scope": "org_public",
        "content": """# 企业知识平台使用手册

## 使用原则

- 任何资料先放到明确的知识空间，再决定是否共享
- 不要求普通成员理解全部治理规则，只要求知道自己上传到哪里
- 审批、共享、成员变更都要可追溯

## 推荐流程

1. 先确认当前工作部门
2. 选择对应知识空间
3. 上传资料并补一句用途说明
4. 如需跨部门使用，再发起共享
""",
    },
    {
        "knowledge_base_code": "product-playbook",
        "uploader_email": "lena.demo@example.com",
        "title": "季度经营复盘模板",
        "filename": "product-quarterly-retro.md",
        "visibility_scope": "knowledge_base_default",
        "content": """# 季度经营复盘模板

## 必答问题

- 本季度最关键的增长动作是什么
- 哪些需求被证明有效，哪些需要下线
- 下个季度最需要研发配合的三件事

## 会后动作

- 形成复盘结论
- 回填知识空间
- 需要跨部门复用时走共享申请
""",
    },
    {
        "knowledge_base_code": "rd-standards",
        "uploader_email": "chen.demo@example.com",
        "title": "上线前检查清单",
        "filename": "rd-release-checklist.md",
        "visibility_scope": "knowledge_base_default",
        "content": """# 上线前检查清单

## 核心项

- 接口变更是否同步给交付和产品
- 回滚方案是否写入值班手册
- 数据修复脚本是否经过演练
- 文档是否回填到知识空间
""",
    },
    {
        "knowledge_base_code": "delivery-sop",
        "uploader_email": "maya.demo@example.com",
        "title": "现场问题升级路径",
        "filename": "delivery-escalation-path.md",
        "visibility_scope": "knowledge_base_default",
        "content": """# 现场问题升级路径

## 一线判断

- 先确认是否影响客户核心业务
- 判断是环境问题、数据问题还是产品缺陷
- 需要研发介入时，附上复现步骤和影响范围

## 沟通原则

- 一次同步结论、下一步负责人和预计更新时间
- 现场问题处理完毕后回填复盘文档
""",
    },
]

DEMO_JOIN_REQUESTS = [
    {
        "user_email": "nora.demo@example.com",
        "target_department_code": "dept-rd",
        "requested_role_code": "knowledge_operator",
        "reason": "需要长期协作研发规范整理与文档维护。",
        "status": "approved",
        "reviewer_email": "chen.demo@example.com",
        "review_comment": "已加入协作部门，后续负责规范梳理。",
    },
    {
        "user_email": "jack.demo@example.com",
        "target_department_code": "dept-product",
        "requested_role_code": "department_member",
        "reason": "负责接入产品需求资料整理和经营周报维护。",
        "status": "pending",
        "reviewer_email": None,
        "review_comment": None,
    },
]

DEMO_SHARE_REQUESTS = [
    {
        "knowledge_base_code": "rd-standards",
        "source_department_code": "dept-rd",
        "target_department_code": "dept-delivery",
        "requested_by": "chen.demo@example.com",
        "reason": "交付团队需要复用上线检查清单和故障升级规范。",
        "status": "approved",
        "reviewer_email": "maya.demo@example.com",
        "review_comment": "同意共享给交付服务部作为执行标准。",
    },
    {
        "knowledge_base_code": "delivery-sop",
        "source_department_code": "dept-delivery",
        "target_department_code": "dept-product",
        "requested_by": "maya.demo@example.com",
        "reason": "希望产品团队在需求评审时同步考虑现场交付约束。",
        "status": "pending",
        "reviewer_email": None,
        "review_comment": None,
    },
]


def _build_document_storage_path(document_id: int, file_extension: str) -> Path:
    normalized_extension = file_extension if file_extension.startswith(".") else f".{file_extension}"
    return UPLOAD_DIR / f"knowledge_document_{document_id}{normalized_extension.lower()}"


async def _seed_users(session) -> dict[str, User]:
    existing_result = await session.execute(select(User))
    users_by_email = {user.email.lower(): user for user in existing_result.scalars().all()}

    for spec in DEMO_USERS:
        email = spec["email"].lower()
        if email in users_by_email:
            continue

        user = User(
            email=email,
            username=spec["username"],
            hashed_password=hash_password(spec["password"]),
            is_active=True,
        )
        session.add(user)
        await session.flush()
        users_by_email[email] = user

    return users_by_email


async def _seed_departments(session, users_by_email: dict[str, User]) -> dict[str, Department]:
    existing_result = await session.execute(select(Department))
    departments_by_code = {department.code: department for department in existing_result.scalars().all()}

    for spec in DEMO_DEPARTMENTS:
        if spec["code"] in departments_by_code:
            department = departments_by_code[spec["code"]]
            manager = users_by_email[spec["manager_email"]]
            if department.manager_user_id is None:
                department.manager_user_id = manager.id
            continue

        parent_department = (
            departments_by_code.get(spec["parent_code"]) if spec["parent_code"] is not None else None
        )
        manager = users_by_email[spec["manager_email"]]
        department = Department(
            parent_id=parent_department.id if parent_department else None,
            manager_user_id=manager.id,
            code=spec["code"],
            name=spec["name"],
            full_name=spec["full_name"],
            status="active",
        )
        session.add(department)
        await session.flush()
        departments_by_code[department.code] = department

    return departments_by_code


async def _seed_memberships(session, users_by_email: dict[str, User], departments_by_code: dict[str, Department]) -> None:
    existing_result = await session.execute(select(DepartmentMembership))
    existing_keys = {
        (membership.user_id, membership.department_id): membership for membership in existing_result.scalars().all()
    }

    for spec in DEMO_MEMBERSHIPS:
        user = users_by_email[spec["email"]]
        department = departments_by_code[spec["department_code"]]
        key = (user.id, department.id)
        if key in existing_keys:
            continue

        approver = users_by_email[spec["approved_by"]]
        membership = DepartmentMembership(
            user_id=user.id,
            department_id=department.id,
            membership_type=spec["membership_type"],
            is_primary=spec["is_primary"],
            status="active",
            approved_by=approver.id,
        )
        session.add(membership)
        await session.flush()
        existing_keys[key] = membership


async def _seed_join_requests(
    session,
    users_by_email: dict[str, User],
    departments_by_code: dict[str, Department],
) -> None:
    existing_result = await session.execute(select(DepartmentJoinRequest))
    existing_keys = {
        (item.user_id, item.target_department_id, item.status): item for item in existing_result.scalars().all()
    }

    for spec in DEMO_JOIN_REQUESTS:
        user = users_by_email[spec["user_email"]]
        department = departments_by_code[spec["target_department_code"]]
        key = (user.id, department.id, spec["status"])
        if key in existing_keys:
            continue

        reviewer = users_by_email.get(spec["reviewer_email"]) if spec["reviewer_email"] else None
        reviewed_at = datetime.now(timezone.utc) if reviewer else None
        request = DepartmentJoinRequest(
            user_id=user.id,
            target_department_id=department.id,
            requested_role_code=spec["requested_role_code"],
            reason=spec["reason"],
            status=spec["status"],
            reviewer_user_id=reviewer.id if reviewer else None,
            review_comment=spec["review_comment"],
            reviewed_at=reviewed_at,
        )
        session.add(request)
        await session.flush()
        existing_keys[key] = request


async def _seed_knowledge_bases(
    session,
    users_by_email: dict[str, User],
    departments_by_code: dict[str, Department],
) -> dict[str, KnowledgeBase]:
    existing_result = await session.execute(select(KnowledgeBase))
    bases_by_code = {item.code: item for item in existing_result.scalars().all()}

    for spec in DEMO_KNOWLEDGE_BASES:
        if spec["code"] in bases_by_code:
            continue

        department = departments_by_code[spec["department_code"]]
        creator = users_by_email[spec["created_by"]]
        knowledge_base = KnowledgeBase(
            department_id=department.id,
            created_by=creator.id,
            code=spec["code"],
            name=spec["name"],
            description=spec["description"],
            visibility_scope=spec["visibility_scope"],
            status="active",
        )
        session.add(knowledge_base)
        await session.flush()
        bases_by_code[knowledge_base.code] = knowledge_base

    return bases_by_code


async def _seed_documents(
    session,
    users_by_email: dict[str, User],
    bases_by_code: dict[str, KnowledgeBase],
) -> None:
    existing_result = await session.execute(select(KnowledgeDocument))
    existing_keys = {
        (item.knowledge_base_id, item.filename): item for item in existing_result.scalars().all()
    }

    UPLOAD_DIR.mkdir(exist_ok=True)

    for spec in DEMO_DOCUMENTS:
        knowledge_base = bases_by_code[spec["knowledge_base_code"]]
        key = (knowledge_base.id, spec["filename"])
        if key in existing_keys:
            document = existing_keys[key]
            file_path = _build_document_storage_path(document.id, document.file_extension)
            if not file_path.exists():
                file_path.write_text(spec["content"], encoding="utf-8")
            continue

        uploader = users_by_email[spec["uploader_email"]]
        extension = Path(spec["filename"]).suffix.lower() or ".md"
        document = KnowledgeDocument(
            knowledge_base_id=knowledge_base.id,
            department_id=knowledge_base.department_id,
            uploader_user_id=uploader.id,
            title=spec["title"],
            filename=spec["filename"],
            file_extension=extension,
            visibility_scope=spec["visibility_scope"],
            status="active",
            chunks_count=max(3, len([line for line in spec["content"].splitlines() if line.strip()])),
        )
        session.add(document)
        await session.flush()

        file_path = _build_document_storage_path(document.id, extension)
        file_path.write_text(spec["content"], encoding="utf-8")
        existing_keys[key] = document


async def _seed_share_requests(
    session,
    users_by_email: dict[str, User],
    departments_by_code: dict[str, Department],
    bases_by_code: dict[str, KnowledgeBase],
) -> None:
    existing_request_result = await session.execute(select(KnowledgeBaseShareRequest))
    existing_request_keys = {
        (item.knowledge_base_id, item.target_department_id, item.status): item
        for item in existing_request_result.scalars().all()
    }

    existing_share_result = await session.execute(select(KnowledgeBaseShare))
    existing_share_keys = {
        (item.knowledge_base_id, item.target_department_id): item for item in existing_share_result.scalars().all()
    }

    for spec in DEMO_SHARE_REQUESTS:
        knowledge_base = bases_by_code[spec["knowledge_base_code"]]
        source_department = departments_by_code[spec["source_department_code"]]
        target_department = departments_by_code[spec["target_department_code"]]
        requester = users_by_email[spec["requested_by"]]
        reviewer = users_by_email.get(spec["reviewer_email"]) if spec["reviewer_email"] else None

        request_key = (knowledge_base.id, target_department.id, spec["status"])
        if request_key not in existing_request_keys:
            share_request = KnowledgeBaseShareRequest(
                knowledge_base_id=knowledge_base.id,
                source_department_id=source_department.id,
                target_department_id=target_department.id,
                requested_by=requester.id,
                reason=spec["reason"],
                status=spec["status"],
                reviewer_user_id=reviewer.id if reviewer else None,
                review_comment=spec["review_comment"],
                reviewed_at=datetime.now(timezone.utc) if reviewer else None,
            )
            session.add(share_request)
            await session.flush()
            existing_request_keys[request_key] = share_request

        if spec["status"] != "approved":
            continue

        share_key = (knowledge_base.id, target_department.id)
        if share_key in existing_share_keys:
            continue

        share = KnowledgeBaseShare(
            knowledge_base_id=knowledge_base.id,
            source_department_id=source_department.id,
            target_department_id=target_department.id,
            created_by=reviewer.id if reviewer else requester.id,
            status="active",
        )
        session.add(share)
        await session.flush()
        existing_share_keys[share_key] = share


async def seed_demo_data() -> None:
    async with AsyncSessionLocal() as session:
        users_by_email = await _seed_users(session)
        departments_by_code = await _seed_departments(session, users_by_email)
        await _seed_memberships(session, users_by_email, departments_by_code)
        await _seed_join_requests(session, users_by_email, departments_by_code)
        bases_by_code = await _seed_knowledge_bases(session, users_by_email, departments_by_code)
        await _seed_documents(session, users_by_email, bases_by_code)
        await _seed_share_requests(session, users_by_email, departments_by_code, bases_by_code)
        await session.commit()

    logger.info("开发演示数据已准备完成。可使用 demo_lena / %s 登录查看审批和空间流转。", DEMO_PASSWORD)
