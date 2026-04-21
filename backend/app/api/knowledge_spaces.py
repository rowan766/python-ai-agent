from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.core.http import paginated_response, success_response
from app.models import Department, KnowledgeSpace, KnowledgeSpaceMember, KnowledgeSpaceShare, Role, User
from app.schemas import (
    ApiResponse,
    KnowledgeSpaceItem,
    KnowledgeSpaceMemberItem,
    KnowledgeSpaceMemberUpsertRequest,
    KnowledgeSpaceShareItem,
    KnowledgeSpaceShareUpsertRequest,
    KnowledgeSpaceUpsertRequest,
    PageData,
)
from app.services.knowledge_space_permissions import (
    build_space_access_clause,
    ensure_space_has_owner,
    normalize_permission_level,
    normalize_share_target_type,
    normalize_space_role,
)
from app.services.serializers import serialize_knowledge_space, serialize_knowledge_space_member, serialize_knowledge_space_share


router = APIRouter(prefix="/knowledge-space", tags=["知识空间"])
VALID_VISIBILITY_MODES = {"private", "department", "shared"}


def _knowledge_space_query():
    return (
        select(KnowledgeSpace)
        .options(selectinload(KnowledgeSpace.creator))
        .options(selectinload(KnowledgeSpace.owner_department))
        .options(selectinload(KnowledgeSpace.members).selectinload(KnowledgeSpaceMember.user))
        .options(selectinload(KnowledgeSpace.shares))
    )


def _normalize_visibility_mode(value: str | None) -> str:
    normalized = (value or "private").strip().lower()
    if normalized not in VALID_VISIBILITY_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="visibilityMode 仅支持 private、department、shared",
        )
    return normalized


def _get_space_or_404(db: DbSession, current_user, space_id: int, *, action: str = "read") -> KnowledgeSpace:
    statement = _knowledge_space_query().where(KnowledgeSpace.id == space_id)
    access_clause = build_space_access_clause(db, current_user, action=action)
    if access_clause is not None:
        statement = statement.where(access_clause)
    space = db.scalar(statement)
    if not space:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识空间不存在")
    return space


def _get_space_member_or_404(db: DbSession, space_id: int, member_id: int) -> KnowledgeSpaceMember:
    member = db.scalar(
        select(KnowledgeSpaceMember)
        .options(selectinload(KnowledgeSpaceMember.user))
        .where(KnowledgeSpaceMember.id == member_id, KnowledgeSpaceMember.space_id == space_id)
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="空间成员不存在")
    return member


def _get_space_share_or_404(db: DbSession, space_id: int, share_id: int) -> KnowledgeSpaceShare:
    share = db.scalar(
        select(KnowledgeSpaceShare).where(
            KnowledgeSpaceShare.id == share_id,
            KnowledgeSpaceShare.space_id == space_id,
        )
    )
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="空间共享记录不存在")
    return share


def _assert_share_target_exists(db: DbSession, target_type: str, target_id: int) -> None:
    model_map = {
        "department": Department,
        "role": Role,
        "user": User,
    }
    model = model_map[target_type]
    target = db.scalar(select(model).where(model.id == target_id))
    if not target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="共享目标不存在")


@router.get(
    "",
    summary="获取知识空间列表",
    response_model=ApiResponse[PageData[KnowledgeSpaceItem]],
)
def get_knowledge_space_list(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, title="页码", description="分页页码，从 1 开始"),
    pageSize: int = Query(default=10, ge=1, le=1000, title="每页条数", description="每页返回的知识空间数量"),
    status_filter: int | None = Query(default=None, alias="status", title="状态", description="按空间状态筛选"),
    keyword: str | None = Query(default=None, title="关键词", description="按空间名称模糊搜索"),
) -> dict:
    filters: list[object] = []
    access_clause = build_space_access_clause(db, current_user, action="read")
    if access_clause is not None:
        filters.append(access_clause)
    if status_filter is not None:
        filters.append(KnowledgeSpace.status == status_filter)
    if keyword and keyword.strip():
        filters.append(KnowledgeSpace.name.ilike(f"%{keyword.strip()}%"))

    total = db.scalar(select(func.count()).select_from(KnowledgeSpace).where(*filters)) or 0
    spaces = db.scalars(
        _knowledge_space_query()
        .where(*filters)
        .order_by(KnowledgeSpace.updated_at.desc(), KnowledgeSpace.id.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).unique().all()
    return paginated_response([serialize_knowledge_space(space) for space in spaces], total, page, pageSize)


@router.post(
    "",
    summary="创建知识空间",
    response_model=ApiResponse[KnowledgeSpaceItem],
)
def create_knowledge_space(
    payload: KnowledgeSpaceUpsertRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    space = KnowledgeSpace(
        name=payload.name.strip(),
        description=(payload.description or "").strip() or None,
        status=payload.status,
        created_by=current_user.id,
        owner_department_id=payload.ownerDepartmentId or current_user.department_id,
        visibility_mode=_normalize_visibility_mode(payload.visibilityMode),
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
    db.commit()
    space = _get_space_or_404(db, current_user, space.id, action="read")
    return success_response(serialize_knowledge_space(space, include_members=True, include_shares=True))


@router.get(
    "/{space_id}",
    summary="获取知识空间详情",
    response_model=ApiResponse[KnowledgeSpaceItem],
)
def get_knowledge_space_detail(
    space_id: Annotated[int, Path(title="知识空间 ID", description="要查看的知识空间主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    return success_response(
        serialize_knowledge_space(
            _get_space_or_404(db, current_user, space_id, action="read"),
            include_members=True,
            include_shares=True,
        )
    )


@router.put(
    "/{space_id}",
    summary="更新知识空间",
    response_model=ApiResponse[KnowledgeSpaceItem],
)
def update_knowledge_space(
    space_id: Annotated[int, Path(title="知识空间 ID", description="要更新的知识空间主键 ID")],
    payload: KnowledgeSpaceUpsertRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    space = _get_space_or_404(db, current_user, space_id, action="manage")
    space.name = payload.name.strip()
    space.description = (payload.description or "").strip() or None
    space.status = payload.status
    space.owner_department_id = payload.ownerDepartmentId or current_user.department_id
    space.visibility_mode = _normalize_visibility_mode(payload.visibilityMode)
    db.commit()
    space = _get_space_or_404(db, current_user, space_id, action="read")
    return success_response(serialize_knowledge_space(space, include_members=True, include_shares=True))


@router.post(
    "/{space_id}/members",
    summary="新增或更新知识空间成员",
    response_model=ApiResponse[KnowledgeSpaceMemberItem],
)
def upsert_knowledge_space_member(
    space_id: Annotated[int, Path(title="知识空间 ID", description="要配置成员的知识空间主键 ID")],
    payload: KnowledgeSpaceMemberUpsertRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    _get_space_or_404(db, current_user, space_id, action="manage")
    user = db.scalar(select(User).where(User.id == payload.userId, User.status == 1))
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户不存在或已停用")

    space_role = normalize_space_role(payload.spaceRole)
    member = db.scalar(
        select(KnowledgeSpaceMember)
        .options(selectinload(KnowledgeSpaceMember.user))
        .where(KnowledgeSpaceMember.space_id == space_id, KnowledgeSpaceMember.user_id == payload.userId)
    )
    if member:
        if member.space_role == "owner" and space_role != "owner":
            ensure_space_has_owner(db, space_id, excluding_member_id=member.id)
        member.space_role = space_role
    else:
        member = KnowledgeSpaceMember(
            space_id=space_id,
            user_id=payload.userId,
            space_role=space_role,
        )
        db.add(member)

    db.commit()
    member = db.scalar(
        select(KnowledgeSpaceMember)
        .options(selectinload(KnowledgeSpaceMember.user))
        .where(KnowledgeSpaceMember.space_id == space_id, KnowledgeSpaceMember.user_id == payload.userId)
    )
    return success_response(serialize_knowledge_space_member(member), message="成员已保存")


@router.delete(
    "/{space_id}/members/{member_id}",
    summary="删除知识空间成员",
    response_model=ApiResponse[None],
)
def delete_knowledge_space_member(
    space_id: Annotated[int, Path(title="知识空间 ID", description="所属知识空间主键 ID")],
    member_id: Annotated[int, Path(title="成员 ID", description="要删除的空间成员主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    _get_space_or_404(db, current_user, space_id, action="manage")
    member = _get_space_member_or_404(db, space_id, member_id)
    if member.space_role == "owner":
        ensure_space_has_owner(db, space_id, excluding_member_id=member.id)
    db.delete(member)
    db.commit()
    return success_response(message="成员已删除")


@router.post(
    "/{space_id}/shares",
    summary="新增或更新知识空间共享",
    response_model=ApiResponse[KnowledgeSpaceShareItem],
)
def upsert_knowledge_space_share(
    space_id: Annotated[int, Path(title="知识空间 ID", description="要配置共享的知识空间主键 ID")],
    payload: KnowledgeSpaceShareUpsertRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    _get_space_or_404(db, current_user, space_id, action="share")
    target_type = normalize_share_target_type(payload.targetType)
    permission_level = normalize_permission_level(payload.permissionLevel)
    _assert_share_target_exists(db, target_type, payload.targetId)

    share = db.scalar(
        select(KnowledgeSpaceShare).where(
            KnowledgeSpaceShare.space_id == space_id,
            KnowledgeSpaceShare.target_type == target_type,
            KnowledgeSpaceShare.target_id == payload.targetId,
        )
    )
    if share:
        share.permission_level = permission_level
    else:
        share = KnowledgeSpaceShare(
            space_id=space_id,
            target_type=target_type,
            target_id=payload.targetId,
            permission_level=permission_level,
        )
        db.add(share)

    db.commit()
    share = db.scalar(
        select(KnowledgeSpaceShare).where(
            KnowledgeSpaceShare.space_id == space_id,
            KnowledgeSpaceShare.target_type == target_type,
            KnowledgeSpaceShare.target_id == payload.targetId,
        )
    )
    return success_response(serialize_knowledge_space_share(share), message="共享配置已保存")


@router.delete(
    "/{space_id}/shares/{share_id}",
    summary="删除知识空间共享",
    response_model=ApiResponse[None],
)
def delete_knowledge_space_share(
    space_id: Annotated[int, Path(title="知识空间 ID", description="所属知识空间主键 ID")],
    share_id: Annotated[int, Path(title="共享 ID", description="要删除的共享记录主键 ID")],
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    _get_space_or_404(db, current_user, space_id, action="share")
    share = _get_space_share_or_404(db, space_id, share_id)
    db.delete(share)
    db.commit()
    return success_response(message="共享配置已删除")
