from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=255)
    captchaId: str = Field(min_length=1, max_length=100)
    captchaCode: str = Field(min_length=1, max_length=10)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=255)
    email: str | None = Field(default=None, max_length=100)
    departmentId: int | None = None
    status: int = 1


class UserUpdateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str | None = Field(default=None, max_length=100)
    departmentId: int | None = None
    status: int = 1


class AssignRolesRequest(BaseModel):
    roleIds: list[int] = Field(default_factory=list)


class ProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    gender: int = 0


class ChangePasswordRequest(BaseModel):
    oldPassword: str = Field(min_length=1, max_length=255)
    newPassword: str = Field(min_length=6, max_length=255)
    confirmPassword: str = Field(min_length=6, max_length=255)


class AdminChangePasswordRequest(BaseModel):
    newPassword: str = Field(min_length=6, max_length=255)
    confirmPassword: str = Field(min_length=6, max_length=255)


class RoleUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=200)
    dataScope: int = 1
    sort: int = 0
    status: int = 1


class RoleMenusRequest(BaseModel):
    menuIds: list[int] = Field(default_factory=list)


class RoleDataScopeRequest(BaseModel):
    dataScope: int = 1
    departmentIds: list[int] = Field(default_factory=list)


class MenuUpsertRequest(BaseModel):
    parentId: int | None = None
    name: str | None = Field(default=None, max_length=50)
    title: str = Field(min_length=1, max_length=50)
    type: str = Field(min_length=1, max_length=20)
    path: str | None = Field(default=None, max_length=200)
    component: str | None = Field(default=None, max_length=200)
    permission: str | None = Field(default=None, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    sort: int = 0
    visible: int = 1
    status: int = 1


class StatusPatchRequest(BaseModel):
    status: int


class DepartmentUpsertRequest(BaseModel):
    parentId: int | None = None
    leaderId: int | None = None
    name: str = Field(min_length=1, max_length=50)
    code: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=100)
    sort: int = 0
    description: str | None = Field(default=None, max_length=200)


class DictTypeUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=200)
    sort: int = 0
    status: int = 1


class DictDataUpsertRequest(BaseModel):
    dictTypeId: int
    label: str = Field(min_length=1, max_length=50)
    value: str = Field(min_length=1, max_length=50)
    sort: int = 0
    cssClass: str | None = Field(default=None, max_length=50)
    remark: str | None = Field(default=None, max_length=200)
    status: int = 1
