# 处理聊天请求，支持流式输出（SSE）。StreamingResponse 是 FastAPI 内置的，相当于你在 NestJS 里手动写 SSE 的封装版本。

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, is_platform_admin
from app.core.access import expand_department_descendants, get_accessible_knowledge_base_ids
from app.core.database import get_db
from app.core.llm import client, DEFAULT_MODEL
from app.core.rag.retriever import retrieve_documents
from app.core.system_handbook import build_system_handbook_context
from app.models.department import Department, DepartmentJoinRequest, DepartmentMembership
from app.models.knowledge import KnowledgeBase, KnowledgeBaseShareRequest, KnowledgeDocument
from app.models.schemas import ChatRequest
from app.models.user import User

router = APIRouter()


def _truncate_text(content: str, limit: int = 420) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _format_named_list(items: list[str], empty_text: str = "暂无") -> str:
    if not items:
        return empty_text
    if len(items) <= 6:
        return "、".join(items)
    preview = "、".join(items[:6])
    return f"{preview} 等 {len(items)} 项"


async def _load_user_snapshot(
    db: AsyncSession,
    current_user: User,
    active_department_id: int | None,
) -> dict:
    membership_result = await db.execute(
        select(DepartmentMembership, Department)
        .join(Department, Department.id == DepartmentMembership.department_id)
        .where(
            and_(
                DepartmentMembership.user_id == current_user.id,
                DepartmentMembership.status == "active",
                Department.status == "active",
            )
        )
        .order_by(DepartmentMembership.is_primary.desc(), Department.name.asc())
    )
    membership_rows = membership_result.all()

    primary_department_id: int | None = None
    primary_department_name = "--"
    current_department_id: int | None = None
    current_department_name = "--"
    membership_descriptions: list[str] = []
    active_membership_department_ids: set[int] = set()

    for membership, department in membership_rows:
        active_membership_department_ids.add(department.id)
        label = "主归属部门" if membership.is_primary else "协作部门"
        membership_descriptions.append(f"{department.name}（{label}）")
        if membership.is_primary and primary_department_id is None:
            primary_department_id = department.id
            primary_department_name = department.name
        if active_department_id == department.id:
            current_department_id = department.id
            current_department_name = department.name

    if current_department_name == "--" and membership_rows:
        current_department_id = primary_department_id or membership_rows[0][1].id
        current_department_name = primary_department_name

    managed_result = await db.execute(
        select(Department)
        .where(
            and_(
                Department.manager_user_id == current_user.id,
                Department.status == "active",
            )
        )
        .order_by(Department.name.asc())
    )
    managed_departments = list(managed_result.scalars().all())
    managed_department_names = [department.name for department in managed_departments]
    managed_department_ids = [department.id for department in managed_departments]

    manageable_scope_ids: list[int] = []
    if managed_department_ids:
        department_result = await db.execute(
            select(Department).where(Department.status == "active").order_by(Department.id.asc())
        )
        manageable_scope_ids = expand_department_descendants(
            list(department_result.scalars().all()),
            managed_department_ids,
        )

    organization_status = "ready" if membership_rows else "pending_assignment"
    current_department_description = (
        current_department_name
        if active_department_id in active_membership_department_ids or active_department_id is None
        else f"{primary_department_name}（忽略了无权限的前端部门上下文 {active_department_id}）"
    )

    return {
        "primary_department_id": primary_department_id,
        "primary_department_name": primary_department_name,
        "current_department_id": current_department_id,
        "current_department_name": current_department_name,
        "current_department_description": current_department_description,
        "membership_descriptions": membership_descriptions,
        "active_membership_department_ids": active_membership_department_ids,
        "managed_department_names": managed_department_names,
        "managed_department_ids": managed_department_ids,
        "manageable_scope_ids": manageable_scope_ids,
        "organization_status": organization_status,
    }


def _build_user_context(
    current_user: User,
    snapshot: dict,
) -> str:
    lines = [
        "你是企业知识平台内置助手，需要优先回答“这个系统里的用户与权限”问题。",
        "当用户问“我属于哪个部门”“我现在在哪个部门视角下工作”“我能访问什么”“我是谁的审批人”时，必须优先依据下面的用户上下文回答，不要编造。",
        "这里的“当前工作部门”指用户当前在前端选中的部门视角；“主归属部门/协作部门”指系统里的真实组织归属。",
        "当用户问“这个系统是干什么的”“知识空间/审批/文档/组织流程是什么”“工作台里有什么信息”时，可以结合后面的系统手册和实时业务摘要回答。",
        "当用户问“我现在有多少待办”“我当前部门多少人”“我能访问多少文档/空间”时，优先依据实时业务摘要回答。",
        "如果上下文里没有答案，就明确说明当前系统上下文不足，而不是猜测。",
        "",
        f"当前登录用户：{current_user.username} <{current_user.email}>",
        f"平台管理员：{'是' if is_platform_admin(current_user) else '否'}",
        f"组织状态：{snapshot['organization_status']}",
        f"主归属部门：{snapshot['primary_department_name']}",
        f"当前工作部门：{snapshot['current_department_description']}",
        f"部门归属列表：{_format_named_list(snapshot['membership_descriptions'], empty_text='暂无部门归属')}",
        f"当前负责审批的部门：{_format_named_list(snapshot['managed_department_names'])}",
    ]

    return "\n".join(lines)


async def _build_realtime_system_context(
    db: AsyncSession,
    current_user: User,
    snapshot: dict,
    accessible_knowledge_base_ids: list[int],
) -> str:
    current_department_id = snapshot["current_department_id"]
    current_department_name = snapshot["current_department_name"]

    current_department_member_count = 0
    current_department_manager_name = "未设置"
    current_department_knowledge_base_count = 0
    current_department_document_count = 0

    if current_department_id is not None:
        manager_result = await db.execute(
            select(Department, User)
            .outerjoin(User, User.id == Department.manager_user_id)
            .where(Department.id == current_department_id)
        )
        manager_row = manager_result.first()
        if manager_row:
            _department, manager = manager_row
            if manager:
                current_department_manager_name = f"{manager.username} <{manager.email}>"

        member_count_result = await db.execute(
            select(func.count(DepartmentMembership.id))
            .join(User, User.id == DepartmentMembership.user_id)
            .where(
                and_(
                    DepartmentMembership.department_id == current_department_id,
                    DepartmentMembership.status == "active",
                    User.is_active.is_(True),
                )
            )
        )
        current_department_member_count = member_count_result.scalar_one()

        current_department_knowledge_base_count_result = await db.execute(
            select(func.count(KnowledgeBase.id)).where(
                and_(
                    KnowledgeBase.department_id == current_department_id,
                    KnowledgeBase.status == "active",
                )
            )
        )
        current_department_knowledge_base_count = current_department_knowledge_base_count_result.scalar_one()

        current_department_document_count_result = await db.execute(
            select(func.count(KnowledgeDocument.id)).where(
                and_(
                    KnowledgeDocument.department_id == current_department_id,
                    KnowledgeDocument.status == "active",
                )
            )
        )
        current_department_document_count = current_department_document_count_result.scalar_one()

    accessible_knowledge_base_names: list[str] = []
    accessible_document_count = 0
    if accessible_knowledge_base_ids:
        accessible_knowledge_base_result = await db.execute(
            select(KnowledgeBase.name)
            .where(
                and_(
                    KnowledgeBase.id.in_(accessible_knowledge_base_ids),
                    KnowledgeBase.status == "active",
                )
            )
            .order_by(KnowledgeBase.name.asc())
        )
        accessible_knowledge_base_names = list(accessible_knowledge_base_result.scalars().all())

        accessible_document_count_result = await db.execute(
            select(func.count(KnowledgeDocument.id)).where(
                and_(
                    KnowledgeDocument.status == "active",
                    KnowledgeDocument.knowledge_base_id.in_(accessible_knowledge_base_ids),
                )
            )
        )
        accessible_document_count = accessible_document_count_result.scalar_one()

    if is_platform_admin(current_user):
        pending_join_count_result = await db.execute(
            select(func.count(DepartmentJoinRequest.id)).where(DepartmentJoinRequest.status == "pending")
        )
        pending_share_count_result = await db.execute(
            select(func.count(KnowledgeBaseShareRequest.id)).where(
                KnowledgeBaseShareRequest.status == "pending"
            )
        )
    else:
        managed_department_ids = snapshot["managed_department_ids"]
        manageable_scope_ids = snapshot["manageable_scope_ids"]

        if managed_department_ids:
            pending_join_count_result = await db.execute(
                select(func.count(DepartmentJoinRequest.id)).where(
                    and_(
                        DepartmentJoinRequest.status == "pending",
                        DepartmentJoinRequest.target_department_id.in_(managed_department_ids),
                    )
                )
            )
        else:
            pending_join_count_result = None

        if manageable_scope_ids:
            pending_share_count_result = await db.execute(
                select(func.count(KnowledgeBaseShareRequest.id)).where(
                    and_(
                        KnowledgeBaseShareRequest.status == "pending",
                        KnowledgeBaseShareRequest.target_department_id.in_(manageable_scope_ids),
                    )
                )
            )
        else:
            pending_share_count_result = None

    pending_join_count = pending_join_count_result.scalar_one() if pending_join_count_result else 0
    pending_share_count = pending_share_count_result.scalar_one() if pending_share_count_result else 0

    my_join_count_result = await db.execute(
        select(func.count(DepartmentJoinRequest.id)).where(DepartmentJoinRequest.user_id == current_user.id)
    )
    my_share_count_result = await db.execute(
        select(func.count(KnowledgeBaseShareRequest.id)).where(
            KnowledgeBaseShareRequest.requested_by == current_user.id
        )
    )
    my_join_count = my_join_count_result.scalar_one()
    my_share_count = my_share_count_result.scalar_one()

    lines = [
        "以下是当前用户的实时业务摘要，回答“现在系统里有什么、我当前能看到什么、我有多少待办”时优先参考：",
        f"当前工作部门名称：{current_department_name}",
        f"当前工作部门负责人：{current_department_manager_name}",
        f"当前工作部门有效成员数：{current_department_member_count}",
        f"当前工作部门名下知识空间数：{current_department_knowledge_base_count}",
        f"当前工作部门名下文档数：{current_department_document_count}",
        f"当前用户可访问知识空间总数：{len(accessible_knowledge_base_ids)}",
        f"当前用户可访问文档总数：{accessible_document_count}",
        f"当前用户可访问知识空间示例：{_format_named_list(accessible_knowledge_base_names)}",
        f"待我处理的组织申请数：{pending_join_count}",
        f"待我处理的共享申请数：{pending_share_count}",
        f"我发起的组织申请数：{my_join_count}",
        f"我发起的共享申请数：{my_share_count}",
    ]
    return "\n".join(lines)


async def _build_knowledge_context(
    query_text: str,
    accessible_knowledge_base_ids: list[int],
) -> str:
    if not query_text.strip():
        return "当前没有检索到相关知识片段。"

    if not accessible_knowledge_base_ids:
        return "当前没有可用的知识片段。"

    results = retrieve_documents(
        query=query_text,
        limit=4,
        knowledge_base_ids=accessible_knowledge_base_ids,
    )
    if not results:
        return "当前没有检索到相关知识片段。"

    lines = ["以下是当前用户权限范围内检索到的参考知识片段，仅在相关时引用："]
    for index, item in enumerate(results, start=1):
        metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
        knowledge_base_name = metadata.get("knowledge_base_name", "--")
        department_name = metadata.get("department_name", "--")
        filename = metadata.get("filename", "--")
        content = item.get("content", "") if isinstance(item, dict) else ""
        lines.append(
            f"{index}. 知识空间：{knowledge_base_name}；部门：{department_name}；文件：{filename}；内容：{_truncate_text(content)}"
        )
    return "\n".join(lines)


@router.post(
    "/chat",
    summary="流式聊天",
    description="发送聊天消息并通过 SSE 返回流式结果，复用当前系统登录态，并自动带入用户上下文、实时业务摘要、系统手册与权限内知识片段。 Send chat messages and receive a streaming SSE response using the active authenticated session, with user context, live business summaries, system handbook context, and accessible knowledge snippets.",
)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    流式聊天接口
    前端通过 EventSource 或 fetch + ReadableStream 接收数据
    每次收到一段文字就推送一条 SSE 消息
    """
    messages = [m.model_dump() for m in request.messages]
    model = request.model or DEFAULT_MODEL
    latest_user_message = next(
        (message["content"] for message in reversed(messages) if message["role"] == "user"),
        "",
    )

    snapshot = await _load_user_snapshot(
        db=db,
        current_user=current_user,
        active_department_id=request.active_department_id,
    )
    accessible_knowledge_base_ids = await get_accessible_knowledge_base_ids(db, current_user)
    user_context = _build_user_context(
        current_user=current_user,
        snapshot=snapshot,
    )
    realtime_system_context = await _build_realtime_system_context(
        db=db,
        current_user=current_user,
        snapshot=snapshot,
        accessible_knowledge_base_ids=accessible_knowledge_base_ids,
    )
    system_handbook_context = build_system_handbook_context(latest_user_message)
    knowledge_context = await _build_knowledge_context(
        query_text=latest_user_message,
        accessible_knowledge_base_ids=accessible_knowledge_base_ids,
    )

    messages = [
        {
            "role": "system",
            "content": "\n\n".join(
                [
                    user_context,
                    realtime_system_context,
                    system_handbook_context,
                    knowledge_context,
                ]
            ),
        },
        *messages,
    ]

    async def generate():
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                # SSE 格式：data: {...}\n\n
                yield f"data: {json.dumps({'content': delta}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
