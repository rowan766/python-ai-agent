from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.core.http import paginated_response, success_response
from app.models import DictData, DictType
from app.schemas import DictDataUpsertRequest, DictTypeUpsertRequest, StatusPatchRequest
from app.services.serializers import serialize_dict_data, serialize_dict_type


type_router = APIRouter(prefix="/dict-type", tags=["数据字典"])
data_router = APIRouter(prefix="/dict-data", tags=["数据字典"])


def _get_dict_type_or_404(db: DbSession, dict_type_id: int) -> DictType:
    dict_type = db.scalar(select(DictType).where(DictType.id == dict_type_id))
    if not dict_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字典类型不存在")
    return dict_type


def _get_dict_data_or_404(db: DbSession, dict_data_id: int) -> DictData:
    dict_data = db.scalar(select(DictData).where(DictData.id == dict_data_id))
    if not dict_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="字典数据不存在")
    return dict_data


@type_router.get("")
def get_dict_type_list(
    db: DbSession,
    _current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=1000),
) -> dict:
    total = db.scalar(select(func.count()).select_from(DictType)) or 0
    items = db.scalars(
        select(DictType)
        .order_by(DictType.sort.asc(), DictType.id.asc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return paginated_response([serialize_dict_type(item) for item in items], total, page, pageSize)


@type_router.post("")
def create_dict_type(payload: DictTypeUpsertRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    if db.scalar(select(DictType).where(DictType.code == payload.code)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="字典编码已存在")
    dict_type = DictType(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        sort=payload.sort,
        status=payload.status,
    )
    db.add(dict_type)
    db.commit()
    db.refresh(dict_type)
    return success_response(serialize_dict_type(dict_type), message="创建成功")


@type_router.get("/{dict_type_id}")
def get_dict_type_detail(dict_type_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    return success_response(serialize_dict_type(_get_dict_type_or_404(db, dict_type_id)))


@type_router.put("/{dict_type_id}")
def update_dict_type(dict_type_id: int, payload: DictTypeUpsertRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    dict_type = _get_dict_type_or_404(db, dict_type_id)
    conflict = db.scalar(select(DictType).where(DictType.code == payload.code, DictType.id != dict_type_id))
    if conflict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="字典编码已存在")
    dict_type.name = payload.name
    dict_type.code = payload.code
    dict_type.description = payload.description
    dict_type.sort = payload.sort
    dict_type.status = payload.status
    db.commit()
    db.refresh(dict_type)
    return success_response(serialize_dict_type(dict_type), message="更新成功")


@type_router.patch("/{dict_type_id}")
def update_dict_type_status(dict_type_id: int, payload: StatusPatchRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    dict_type = _get_dict_type_or_404(db, dict_type_id)
    dict_type.status = payload.status
    db.commit()
    db.refresh(dict_type)
    return success_response(serialize_dict_type(dict_type), message="状态更新成功")


@type_router.delete("/{dict_type_id}")
def delete_dict_type(dict_type_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    dict_type = _get_dict_type_or_404(db, dict_type_id)
    db.delete(dict_type)
    db.commit()
    return success_response(message="删除成功")


@data_router.get("/type/{code}")
def get_dict_by_code(code: str, db: DbSession, _current_user: CurrentUser) -> dict:
    dict_type = db.scalar(select(DictType).where(DictType.code == code))
    if not dict_type:
        return success_response([])
    items = db.scalars(
        select(DictData)
        .where(DictData.dict_type_id == dict_type.id, DictData.status == 1)
        .order_by(DictData.sort.asc(), DictData.id.asc())
    ).all()
    return success_response([serialize_dict_data(item) for item in items])


@data_router.get("")
def get_dict_data_list(
    db: DbSession,
    _current_user: CurrentUser,
    dictTypeId: int = Query(..., ge=1),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=1000),
) -> dict:
    total = db.scalar(select(func.count()).select_from(DictData).where(DictData.dict_type_id == dictTypeId)) or 0
    items = db.scalars(
        select(DictData)
        .where(DictData.dict_type_id == dictTypeId)
        .order_by(DictData.sort.asc(), DictData.id.asc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    ).all()
    return paginated_response([serialize_dict_data(item) for item in items], total, page, pageSize)


@data_router.post("")
def create_dict_data(payload: DictDataUpsertRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    _get_dict_type_or_404(db, payload.dictTypeId)
    item = DictData(
        dict_type_id=payload.dictTypeId,
        label=payload.label,
        value=payload.value,
        sort=payload.sort,
        css_class=payload.cssClass,
        remark=payload.remark,
        status=payload.status,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return success_response(serialize_dict_data(item), message="创建成功")


@data_router.get("/{dict_data_id}")
def get_dict_data_detail(dict_data_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    return success_response(serialize_dict_data(_get_dict_data_or_404(db, dict_data_id)))


@data_router.put("/{dict_data_id}")
def update_dict_data(dict_data_id: int, payload: DictDataUpsertRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    _get_dict_type_or_404(db, payload.dictTypeId)
    item = _get_dict_data_or_404(db, dict_data_id)
    item.dict_type_id = payload.dictTypeId
    item.label = payload.label
    item.value = payload.value
    item.sort = payload.sort
    item.css_class = payload.cssClass
    item.remark = payload.remark
    item.status = payload.status
    db.commit()
    db.refresh(item)
    return success_response(serialize_dict_data(item), message="更新成功")


@data_router.patch("/{dict_data_id}")
def update_dict_data_status(dict_data_id: int, payload: StatusPatchRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    item = _get_dict_data_or_404(db, dict_data_id)
    item.status = payload.status
    db.commit()
    db.refresh(item)
    return success_response(serialize_dict_data(item), message="状态更新成功")


@data_router.delete("/{dict_data_id}")
def delete_dict_data(dict_data_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    item = _get_dict_data_or_404(db, dict_data_id)
    db.delete(item)
    db.commit()
    return success_response(message="删除成功")
