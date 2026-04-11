from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.http import success_response
from app.models import Department, User
from app.schemas import DepartmentUpsertRequest
from app.services.serializers import build_tree, serialize_department


router = APIRouter(prefix="/department", tags=["部门管理"])


def _get_department_or_404(db: DbSession, department_id: int) -> Department:
    department = db.scalar(select(Department).where(Department.id == department_id))
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="部门不存在")
    return department


def _assert_department_code_unique(db: DbSession, code: str | None, exclude_id: int | None = None) -> None:
    if not code:
        return
    statement = select(Department).where(Department.code == code)
    if exclude_id:
        statement = statement.where(Department.id != exclude_id)
    if db.scalar(statement):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="部门编码已存在")


@router.get("", summary="获取部门列表")
def get_department_list(db: DbSession, _current_user: CurrentUser) -> dict:
    departments = db.scalars(select(Department).order_by(Department.sort.asc(), Department.id.asc())).all()
    return success_response(build_tree([serialize_department(item) for item in departments]))


@router.post("", summary="创建部门")
def create_department(payload: DepartmentUpsertRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    _assert_department_code_unique(db, payload.code)
    department = Department(
        parent_id=payload.parentId,
        leader_id=payload.leaderId,
        name=payload.name,
        code=payload.code,
        phone=payload.phone,
        email=payload.email,
        sort=payload.sort,
        description=payload.description,
        status=1,
    )
    db.add(department)
    db.commit()
    db.refresh(department)
    return success_response(serialize_department(department), message="创建成功")


@router.get("/{department_id}", summary="获取部门详情")
def get_department_detail(department_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    return success_response(serialize_department(_get_department_or_404(db, department_id)))


@router.put("/{department_id}", summary="更新部门")
def update_department(department_id: int, payload: DepartmentUpsertRequest, db: DbSession, _current_user: CurrentUser) -> dict:
    department = _get_department_or_404(db, department_id)
    _assert_department_code_unique(db, payload.code, exclude_id=department_id)
    if payload.parentId == department_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上级部门不能选择自己")

    department.parent_id = payload.parentId
    department.leader_id = payload.leaderId
    department.name = payload.name
    department.code = payload.code
    department.phone = payload.phone
    department.email = payload.email
    department.sort = payload.sort
    department.description = payload.description
    db.commit()
    db.refresh(department)
    return success_response(serialize_department(department), message="更新成功")


@router.delete("/{department_id}", summary="删除部门")
def delete_department(department_id: int, db: DbSession, _current_user: CurrentUser) -> dict:
    department = _get_department_or_404(db, department_id)
    has_children = db.scalar(select(Department.id).where(Department.parent_id == department_id).limit(1))
    if has_children:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="存在子部门，不能删除")
    has_users = db.scalar(select(User.id).where(User.department_id == department_id).limit(1))
    if has_users:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="部门下仍有用户，不能删除")
    db.delete(department)
    db.commit()
    return success_response(message="删除成功")
