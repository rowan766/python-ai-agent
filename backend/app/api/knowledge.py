import re
from datetime import datetime
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.deps import get_current_user, is_platform_admin
from app.core.access import (
    can_manage_department,
    get_accessible_department_ids,
    get_accessible_knowledge_base_ids,
)
from app.core.database import get_db
from app.core.paths import UPLOAD_DIR
from app.core.rag.indexer import index_documents
from app.core.rag.loader import load_documents
from app.models.department import Department
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeBaseShare,
    KnowledgeBaseShareRequest,
    KnowledgeDocument,
)
from app.models.user import User

router = APIRouter()
UPLOAD_DIR.mkdir(exist_ok=True)

VALID_VISIBILITY_SCOPES = {
    "department_private",
    "department_shared",
    "org_public",
    "knowledge_base_default",
}


class KnowledgeBaseCreateRequest(BaseModel):
    department_id: int
    code: str
    name: str
    description: str | None = None
    visibility_scope: str = "department_private"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "department_id": 1,
                "code": "rd-standards",
                "name": "研发规范库",
                "description": "研发部内部开发规范、流程与最佳实践。",
                "visibility_scope": "department_private",
            }
        }
    )


class KnowledgeBaseShareCreateRequest(BaseModel):
    target_department_id: int
    reason: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target_department_id": 2,
                "reason": "希望研发规范库同步开放给交付部门复用。",
            }
        }
    )


class KnowledgeBaseShareDecisionRequest(BaseModel):
    review_comment: str | None = None


def normalize_code(raw_value: str) -> str:
    code = re.sub(r"[^a-z0-9]+", "-", raw_value.strip().lower())
    return code.strip("-")


def serialize_knowledge_base_row(
    knowledge_base: KnowledgeBase,
    department: Department,
    document_count: int = 0,
) -> dict:
    return {
        "id": knowledge_base.id,
        "department_id": department.id,
        "department_name": department.name,
        "code": knowledge_base.code,
        "name": knowledge_base.name,
        "description": knowledge_base.description,
        "visibility_scope": knowledge_base.visibility_scope,
        "status": knowledge_base.status,
        "document_count": document_count,
        "created_by": knowledge_base.created_by,
        "created_at": knowledge_base.created_at,
    }


def serialize_share_request_row(
    share_request: KnowledgeBaseShareRequest,
    knowledge_base: KnowledgeBase,
    source_department: Department,
    target_department: Department,
    requester: User,
) -> dict:
    return {
        "id": share_request.id,
        "knowledge_base_id": knowledge_base.id,
        "knowledge_base_name": knowledge_base.name,
        "source_department_id": source_department.id,
        "source_department_name": source_department.name,
        "target_department_id": target_department.id,
        "target_department_name": target_department.name,
        "requested_by": requester.id,
        "requested_by_username": requester.username,
        "requested_by_email": requester.email,
        "reason": share_request.reason,
        "status": share_request.status,
        "review_comment": share_request.review_comment,
        "submitted_at": share_request.submitted_at,
        "reviewed_at": share_request.reviewed_at,
    }


@router.get(
    "/knowledge-bases",
    summary="知识库空间列表 List Knowledge Bases",
    description="列出当前用户可访问的知识库空间。 List accessible knowledge base spaces for the current user.",
)
async def list_knowledge_bases(
    department_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible_department_ids = await get_accessible_department_ids(db, current_user)
    accessible_knowledge_base_ids = await get_accessible_knowledge_base_ids(db, current_user)
    if not accessible_knowledge_base_ids:
        return {"items": [], "count": 0}

    if department_id is not None and department_id not in accessible_department_ids:
        raise HTTPException(status_code=403, detail="你没有查看该部门知识库空间的权限")

    stmt = (
        select(KnowledgeBase, Department)
        .join(Department, Department.id == KnowledgeBase.department_id)
        .where(
            and_(
                KnowledgeBase.status == "active",
                KnowledgeBase.id.in_(accessible_knowledge_base_ids),
            )
        )
        .order_by(KnowledgeBase.id.desc())
    )

    if department_id is not None:
        stmt = stmt.where(KnowledgeBase.department_id == department_id)

    result = await db.execute(stmt)
    rows = result.all()
    knowledge_base_ids = [knowledge_base.id for knowledge_base, _department in rows]

    document_counts: dict[int, int] = {}
    if knowledge_base_ids:
        count_result = await db.execute(
            select(
                KnowledgeDocument.knowledge_base_id,
                func.count(KnowledgeDocument.id),
            )
            .where(
                and_(
                    KnowledgeDocument.status == "active",
                    KnowledgeDocument.knowledge_base_id.in_(knowledge_base_ids),
                )
            )
            .group_by(KnowledgeDocument.knowledge_base_id)
        )
        document_counts = {
            knowledge_base_id: count
            for knowledge_base_id, count in count_result.all()
        }

    items = [
        serialize_knowledge_base_row(
            knowledge_base=knowledge_base,
            department=department,
            document_count=document_counts.get(knowledge_base.id, 0),
        )
        for knowledge_base, department in rows
    ]
    return {"items": items, "count": len(items)}


@router.post(
    "/knowledge-bases",
    summary="创建知识库空间 Create Knowledge Base",
    description="创建归属某个部门的知识库空间。 Create a knowledge base space owned by a department.",
)
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    department = await db.get(Department, request.department_id)
    if not department or department.status != "active":
        raise HTTPException(status_code=404, detail="目标部门不存在或不可用")

    if not await can_manage_department(db, current_user, department.id):
        raise HTTPException(status_code=403, detail="仅部门负责人或平台管理员可以创建知识库空间")

    code = normalize_code(request.code or request.name)
    name = request.name.strip()
    description = (request.description or "").strip() or None
    visibility_scope = request.visibility_scope.strip()

    if not code or not name:
        raise HTTPException(status_code=400, detail="知识库编码和名称不能为空")
    if visibility_scope not in VALID_VISIBILITY_SCOPES:
        raise HTTPException(status_code=400, detail="知识库可见性配置无效")

    existing_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.code == code))
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该知识库编码已存在")

    knowledge_base = KnowledgeBase(
        department_id=department.id,
        created_by=current_user.id,
        code=code,
        name=name,
        description=description,
        visibility_scope=visibility_scope,
        status="active",
    )
    db.add(knowledge_base)
    await db.commit()
    await db.refresh(knowledge_base)

    return {
        "status": "success",
        "message": "知识库空间创建成功",
        "knowledge_base": serialize_knowledge_base_row(
            knowledge_base=knowledge_base,
            department=department,
            document_count=0,
        ),
    }


@router.get(
    "/documents",
    summary="文档列表 List Documents",
    description="列出当前用户可访问的知识库文档。 List accessible knowledge documents for the current user.",
)
async def list_documents(
    knowledge_base_id: int | None = Query(default=None),
    department_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible_department_ids = await get_accessible_department_ids(db, current_user)
    accessible_knowledge_base_ids = await get_accessible_knowledge_base_ids(db, current_user)
    if not accessible_knowledge_base_ids:
        return {"items": [], "count": 0}

    if department_id is not None and department_id not in accessible_department_ids:
        raise HTTPException(status_code=403, detail="你没有查看该部门文档的权限")

    stmt = (
        select(KnowledgeDocument, KnowledgeBase, Department, User)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id)
        .join(Department, Department.id == KnowledgeDocument.department_id)
        .join(User, User.id == KnowledgeDocument.uploader_user_id)
        .where(
            and_(
                KnowledgeDocument.status == "active",
                KnowledgeDocument.knowledge_base_id.in_(accessible_knowledge_base_ids),
                KnowledgeBase.status == "active",
            )
        )
        .order_by(KnowledgeDocument.id.desc())
    )

    if knowledge_base_id is not None:
        stmt = stmt.where(KnowledgeDocument.knowledge_base_id == knowledge_base_id)
    if department_id is not None:
        stmt = stmt.where(KnowledgeDocument.department_id == department_id)

    result = await db.execute(stmt)
    rows = result.all()
    items = [
        {
            "id": document.id,
            "knowledge_base_id": knowledge_base.id,
            "knowledge_base_name": knowledge_base.name,
            "department_id": department.id,
            "department_name": department.name,
            "title": document.title,
            "filename": document.filename,
            "file_extension": document.file_extension,
            "visibility_scope": document.visibility_scope,
            "status": document.status,
            "chunks_count": document.chunks_count,
            "uploader_user_id": uploader.id,
            "uploader_username": uploader.username,
            "created_at": document.created_at,
        }
        for document, knowledge_base, department, uploader in rows
    ]
    return {"items": items, "count": len(items)}


@router.get(
    "/knowledge-bases/{knowledge_base_id}/shares",
    summary="知识库共享列表 List Knowledge Base Shares",
    description="查看指定知识库空间当前已生效的共享目标部门。 List active share targets for a knowledge base.",
)
async def list_knowledge_base_shares(
    knowledge_base_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    accessible_knowledge_base_ids = await get_accessible_knowledge_base_ids(db, current_user)
    if knowledge_base_id not in accessible_knowledge_base_ids:
        raise HTTPException(status_code=403, detail="你没有查看该知识库共享配置的权限")

    result = await db.execute(
        select(KnowledgeBaseShare, Department)
        .join(Department, Department.id == KnowledgeBaseShare.target_department_id)
        .where(
            and_(
                KnowledgeBaseShare.knowledge_base_id == knowledge_base_id,
                KnowledgeBaseShare.status == "active",
            )
        )
        .order_by(KnowledgeBaseShare.id.desc())
    )

    items = [
        {
            "id": share.id,
            "target_department_id": department.id,
            "target_department_name": department.name,
            "status": share.status,
            "created_at": share.created_at,
        }
        for share, department in result.all()
    ]
    return {"items": items, "count": len(items)}


@router.post(
    "/knowledge-bases/{knowledge_base_id}/share-requests",
    summary="申请共享知识库 Request Knowledge Base Share",
    description="为指定知识库空间发起共享申请，目标部门负责人审批通过后生效。 Request to share a knowledge base with another department.",
)
async def create_knowledge_base_share_request(
    knowledge_base_id: int,
    request: KnowledgeBaseShareCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reason = request.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="共享申请理由不能为空")

    result = await db.execute(
        select(KnowledgeBase, Department)
        .join(Department, Department.id == KnowledgeBase.department_id)
        .where(and_(KnowledgeBase.id == knowledge_base_id, KnowledgeBase.status == "active"))
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="知识库空间不存在")

    knowledge_base, source_department = row
    target_department = await db.get(Department, request.target_department_id)
    if not target_department or target_department.status != "active":
        raise HTTPException(status_code=404, detail="目标部门不存在或不可用")

    if source_department.id == target_department.id:
        raise HTTPException(status_code=400, detail="不需要向同部门发起共享申请")

    if not await can_manage_department(db, current_user, source_department.id):
        raise HTTPException(status_code=403, detail="仅来源部门负责人或平台管理员可发起共享申请")

    existing_share_result = await db.execute(
        select(KnowledgeBaseShare).where(
            and_(
                KnowledgeBaseShare.knowledge_base_id == knowledge_base.id,
                KnowledgeBaseShare.target_department_id == target_department.id,
                KnowledgeBaseShare.status == "active",
            )
        )
    )
    if existing_share_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该知识库已经共享给目标部门")

    existing_request_result = await db.execute(
        select(KnowledgeBaseShareRequest).where(
            and_(
                KnowledgeBaseShareRequest.knowledge_base_id == knowledge_base.id,
                KnowledgeBaseShareRequest.target_department_id == target_department.id,
                KnowledgeBaseShareRequest.status == "pending",
            )
        )
    )
    if existing_request_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已存在待审批的共享申请")

    share_request = KnowledgeBaseShareRequest(
        knowledge_base_id=knowledge_base.id,
        source_department_id=source_department.id,
        target_department_id=target_department.id,
        requested_by=current_user.id,
        reason=reason,
        status="pending",
    )
    db.add(share_request)
    await db.commit()
    await db.refresh(share_request)

    return {
        "status": "success",
        "message": "知识库共享申请已提交",
        "request": {
            "id": share_request.id,
            "knowledge_base_id": knowledge_base.id,
            "knowledge_base_name": knowledge_base.name,
            "target_department_id": target_department.id,
            "target_department_name": target_department.name,
            "reason": share_request.reason,
            "status": share_request.status,
            "submitted_at": share_request.submitted_at,
        },
    }


@router.get(
    "/knowledge-bases/share-requests/my",
    summary="我的知识库共享申请 My Knowledge Base Share Requests",
    description="查看当前用户发起的知识库共享申请。 List knowledge base share requests created by the current user.",
)
async def list_my_knowledge_base_share_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source_department_alias = aliased(Department)
    target_department_alias = aliased(Department)

    result = await db.execute(
        select(
            KnowledgeBaseShareRequest,
            KnowledgeBase,
            source_department_alias,
            target_department_alias,
            User,
        )
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseShareRequest.knowledge_base_id)
        .join(
            source_department_alias,
            source_department_alias.id == KnowledgeBaseShareRequest.source_department_id,
        )
        .join(
            target_department_alias,
            target_department_alias.id == KnowledgeBaseShareRequest.target_department_id,
        )
        .join(User, User.id == KnowledgeBaseShareRequest.requested_by)
        .where(KnowledgeBaseShareRequest.requested_by == current_user.id)
        .order_by(KnowledgeBaseShareRequest.submitted_at.desc())
    )

    items = [
        serialize_share_request_row(
            share_request=share_request,
            knowledge_base=knowledge_base,
            source_department=source_department,
            target_department=target_department,
            requester=requester,
        )
        for share_request, knowledge_base, source_department, target_department, requester in result.all()
    ]
    return {"items": items, "count": len(items)}


@router.get(
    "/knowledge-bases/share-requests/pending",
    summary="待审批知识库共享申请 Pending Knowledge Base Share Requests",
    description="查看当前用户可以审批的知识库共享申请。 List pending knowledge base share requests reviewable by the current user.",
)
async def list_pending_knowledge_base_share_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source_department_alias = aliased(Department)
    target_department_alias = aliased(Department)

    pending_stmt = (
        select(
            KnowledgeBaseShareRequest,
            KnowledgeBase,
            source_department_alias,
            target_department_alias,
            User,
        )
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeBaseShareRequest.knowledge_base_id)
        .join(
            source_department_alias,
            source_department_alias.id == KnowledgeBaseShareRequest.source_department_id,
        )
        .join(
            target_department_alias,
            target_department_alias.id == KnowledgeBaseShareRequest.target_department_id,
        )
        .join(User, User.id == KnowledgeBaseShareRequest.requested_by)
        .where(KnowledgeBaseShareRequest.status == "pending")
        .order_by(KnowledgeBaseShareRequest.submitted_at.asc())
    )

    pending_result = await db.execute(pending_stmt)
    items = []
    for share_request, knowledge_base, source_department, target_department, requester in pending_result.all():
        if not is_platform_admin(current_user) and not await can_manage_department(
            db, current_user, target_department.id
        ):
            continue
        items.append(
            serialize_share_request_row(
                share_request=share_request,
                knowledge_base=knowledge_base,
                source_department=source_department,
                target_department=target_department,
                requester=requester,
            )
        )

    return {"items": items, "count": len(items)}


async def _get_share_request_or_404(db: AsyncSession, request_id: int) -> KnowledgeBaseShareRequest:
    result = await db.execute(
        select(KnowledgeBaseShareRequest).where(KnowledgeBaseShareRequest.id == request_id)
    )
    share_request = result.scalar_one_or_none()
    if not share_request:
        raise HTTPException(status_code=404, detail="共享申请不存在")
    return share_request


@router.post(
    "/knowledge-bases/share-requests/{request_id}/approve",
    summary="通过知识库共享申请 Approve Knowledge Base Share Request",
    description="审批通过知识库共享申请并创建生效的共享关系。 Approve a knowledge base share request and activate the share.",
)
async def approve_knowledge_base_share_request(
    request_id: int,
    request: KnowledgeBaseShareDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    share_request = await _get_share_request_or_404(db, request_id)
    if share_request.status != "pending":
        raise HTTPException(status_code=400, detail="该共享申请已处理，不能重复审批")

    if not await can_manage_department(db, current_user, share_request.target_department_id):
        raise HTTPException(status_code=403, detail="仅目标部门负责人或平台管理员可审批共享申请")

    existing_share_result = await db.execute(
        select(KnowledgeBaseShare).where(
            and_(
                KnowledgeBaseShare.knowledge_base_id == share_request.knowledge_base_id,
                KnowledgeBaseShare.target_department_id == share_request.target_department_id,
                KnowledgeBaseShare.status == "active",
            )
        )
    )
    if existing_share_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该知识库已经共享给目标部门")

    share = KnowledgeBaseShare(
        knowledge_base_id=share_request.knowledge_base_id,
        source_department_id=share_request.source_department_id,
        target_department_id=share_request.target_department_id,
        created_by=current_user.id,
        status="active",
    )
    db.add(share)

    share_request.status = "approved"
    share_request.reviewer_user_id = current_user.id
    share_request.review_comment = (request.review_comment or "").strip() or "审批通过"
    share_request.reviewed_at = datetime.utcnow()
    knowledge_base = await db.get(KnowledgeBase, share_request.knowledge_base_id)
    if knowledge_base and knowledge_base.visibility_scope != "org_public":
        knowledge_base.visibility_scope = "department_shared"

    await db.commit()
    return {"status": "success", "message": "已通过知识库共享申请"}


@router.post(
    "/knowledge-bases/share-requests/{request_id}/reject",
    summary="驳回知识库共享申请 Reject Knowledge Base Share Request",
    description="驳回知识库共享申请。 Reject a knowledge base share request.",
)
async def reject_knowledge_base_share_request(
    request_id: int,
    request: KnowledgeBaseShareDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    share_request = await _get_share_request_or_404(db, request_id)
    if share_request.status != "pending":
        raise HTTPException(status_code=400, detail="该共享申请已处理，不能重复审批")

    if not await can_manage_department(db, current_user, share_request.target_department_id):
        raise HTTPException(status_code=403, detail="仅目标部门负责人或平台管理员可审批共享申请")

    share_request.status = "rejected"
    share_request.reviewer_user_id = current_user.id
    share_request.review_comment = (request.review_comment or "").strip() or "审批拒绝"
    share_request.reviewed_at = datetime.utcnow()

    await db.commit()
    return {"status": "success", "message": "已驳回知识库共享申请"}


@router.post(
    "/documents/upload",
    summary="上传知识文档 Upload Knowledge Document",
    description="上传文档到指定知识库空间，并完成解析、切片、向量化与入库。 Upload a document into a knowledge base, then parse, chunk, embed, and index it.",
)
async def upload_document_to_knowledge_base(
    knowledge_base_id: int = Form(...),
    visibility_scope: str = Form(default="knowledge_base_default"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="没有文件")

    knowledge_base_result = await db.execute(
        select(KnowledgeBase, Department)
        .join(Department, Department.id == KnowledgeBase.department_id)
        .where(
            and_(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.status == "active",
                Department.status == "active",
            )
        )
    )
    row = knowledge_base_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="目标知识库空间不存在或不可用")

    knowledge_base, department = row
    accessible_department_ids = await get_accessible_department_ids(db, current_user)
    if knowledge_base.department_id not in accessible_department_ids:
        raise HTTPException(status_code=403, detail="你没有向该知识库上传文档的权限")

    normalized_visibility_scope = visibility_scope.strip()
    if normalized_visibility_scope not in VALID_VISIBILITY_SCOPES:
        raise HTTPException(status_code=400, detail="文档可见性配置无效")

    source_path = Path(file.filename)
    stored_filename = f"{uuid4().hex}_{source_path.name}"
    file_path = UPLOAD_DIR / stored_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        docs = load_documents(str(file_path))
        if not docs:
            raise HTTPException(
                status_code=400,
                detail="文档解析后没有可用文本内容，请检查文件是否为空，或文件编码是否正确",
            )

        document = KnowledgeDocument(
            knowledge_base_id=knowledge_base.id,
            department_id=department.id,
            uploader_user_id=current_user.id,
            title=source_path.stem,
            filename=source_path.name,
            file_extension=source_path.suffix.lower(),
            visibility_scope=normalized_visibility_scope,
            status="active",
            chunks_count=0,
        )
        db.add(document)
        await db.flush()

        chunk_count = index_documents(
            docs,
            payload_context={
                "department_id": department.id,
                "department_name": department.name,
                "knowledge_base_id": knowledge_base.id,
                "knowledge_base_name": knowledge_base.name,
                "document_id": document.id,
                "document_title": document.title,
                "filename": document.filename,
                "status": "active",
                "visibility_scope": normalized_visibility_scope,
            },
        )
        document.chunks_count = chunk_count
        await db.commit()
        await db.refresh(document)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if file_path.exists():
            file_path.unlink()

    return JSONResponse(
        content=jsonable_encoder(
            {
                "status": "success",
                "message": f"已上传到知识库 {knowledge_base.name}，成功索引 {document.chunks_count} 个片段",
                "document": {
                    "id": document.id,
                    "knowledge_base_id": knowledge_base.id,
                    "knowledge_base_name": knowledge_base.name,
                    "department_id": department.id,
                    "department_name": department.name,
                    "title": document.title,
                    "filename": document.filename,
                    "file_extension": document.file_extension,
                    "visibility_scope": document.visibility_scope,
                    "chunks_count": document.chunks_count,
                    "created_at": document.created_at,
                },
            }
        )
    )
