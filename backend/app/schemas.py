from __future__ import annotations

from typing import Any, Generic, List, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=200, title="业务状态码", description="接口业务状态码，200 表示请求成功")
    message: str = Field(default="success", title="响应消息", description="接口处理结果说明")
    data: T | None = Field(default=None, title="响应数据", description="接口返回的业务数据")


class PageData(BaseModel, Generic[T]):
    list: List[T] = Field(default_factory=list, title="列表数据", description="当前页的数据列表")
    total: int = Field(title="总记录数", description="满足条件的总记录数量")
    page: int = Field(title="当前页码", description="当前返回的数据页码，从 1 开始")
    pageSize: int = Field(title="每页条数", description="每页返回的数据条数")


class LoginRequest(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=50,
        title="用户名",
        description="登录账号用户名",
    )
    password: str = Field(
        min_length=1,
        max_length=255,
        title="密码",
        description="登录账号密码",
    )
    captchaId: str = Field(
        min_length=1,
        max_length=100,
        title="验证码 ID",
        description="获取验证码接口返回的 captchaId",
    )
    captchaCode: str = Field(
        min_length=1,
        max_length=10,
        title="验证码",
        description="验证码图片中看到的字符",
    )


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, title="用户名", description="新建用户的登录用户名")
    password: str = Field(min_length=6, max_length=255, title="登录密码", description="新建用户的初始密码")
    email: str | None = Field(default=None, max_length=100, title="邮箱", description="用户邮箱地址，可为空")
    departmentId: int | None = Field(default=None, title="部门 ID", description="所属部门 ID，可为空")
    status: int = Field(default=1, title="状态", description="用户状态，1 表示启用，0 表示停用")


class UserUpdateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, title="用户名", description="更新后的登录用户名")
    email: str | None = Field(default=None, max_length=100, title="邮箱", description="更新后的邮箱地址")
    departmentId: int | None = Field(default=None, title="部门 ID", description="所属部门 ID，可为空")
    status: int = Field(default=1, title="状态", description="用户状态，1 表示启用，0 表示停用")


class AssignRolesRequest(BaseModel):
    roleIds: list[int] = Field(
        default_factory=list,
        title="角色 ID 列表",
        description="要分配给用户的角色 ID 集合",
    )


class ProfileUpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=50, title="昵称", description="用户昵称")
    email: str | None = Field(default=None, max_length=100, title="邮箱", description="用户邮箱地址")
    phone: str | None = Field(default=None, max_length=20, title="手机号", description="用户联系电话")
    gender: int = Field(default=0, title="性别", description="性别标记，0 未知，1 男，2 女")


class ChangePasswordRequest(BaseModel):
    oldPassword: str = Field(min_length=1, max_length=255, title="原密码", description="当前登录密码")
    newPassword: str = Field(min_length=6, max_length=255, title="新密码", description="新的登录密码")
    confirmPassword: str = Field(
        min_length=6,
        max_length=255,
        title="确认新密码",
        description="再次输入的新密码，需要与新密码保持一致",
    )


class AdminChangePasswordRequest(BaseModel):
    newPassword: str = Field(min_length=6, max_length=255, title="新密码", description="管理员设置的新密码")
    confirmPassword: str = Field(
        min_length=6,
        max_length=255,
        title="确认新密码",
        description="再次输入的新密码，需要与新密码保持一致",
    )


class DocumentReprocessRequest(BaseModel):
    force: bool = Field(
        default=False,
        title="强制重新处理",
        description="是否忽略当前已有的处理中任务并强制重新入队",
    )


class RoleUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50, title="角色名称", description="角色展示名称")
    code: str = Field(min_length=1, max_length=50, title="角色编码", description="角色唯一编码")
    description: str | None = Field(default=None, max_length=200, title="角色说明", description="角色备注说明")
    dataScope: int = Field(default=1, title="数据权限范围", description="数据权限范围标记")
    sort: int = Field(default=0, title="排序值", description="角色排序，值越小越靠前")
    status: int = Field(default=1, title="状态", description="角色状态，1 表示启用，0 表示停用")


class RoleMenusRequest(BaseModel):
    menuIds: list[int] = Field(
        default_factory=list,
        title="菜单 ID 列表",
        description="角色绑定的菜单与按钮 ID 集合",
    )


class RoleDataScopeRequest(BaseModel):
    dataScope: int = Field(default=1, title="数据权限范围", description="角色的数据权限范围标记")
    departmentIds: list[int] = Field(
        default_factory=list,
        title="部门 ID 列表",
        description="数据权限关联的部门 ID 集合",
    )


class MenuUpsertRequest(BaseModel):
    parentId: int | None = Field(default=None, title="上级菜单 ID", description="父级菜单 ID，顶级菜单可为空")
    name: str | None = Field(default=None, max_length=50, title="路由名称", description="前端路由名称")
    title: str = Field(min_length=1, max_length=50, title="菜单标题", description="菜单或按钮的显示名称")
    type: str = Field(
        min_length=1,
        max_length=20,
        title="菜单类型",
        description="菜单类型，可选值为 menu 或 button",
    )
    path: str | None = Field(default=None, max_length=200, title="路由路径", description="前端访问路径")
    component: str | None = Field(default=None, max_length=200, title="组件路径", description="前端组件文件路径")
    permission: str | None = Field(default=None, max_length=100, title="权限标识", description="按钮或接口权限编码")
    icon: str | None = Field(default=None, max_length=50, title="图标", description="菜单图标标识")
    sort: int = Field(default=0, title="排序值", description="菜单排序，值越小越靠前")
    visible: int = Field(default=1, title="是否显示", description="菜单是否显示，1 显示，0 隐藏")
    status: int = Field(default=1, title="状态", description="菜单状态，1 表示启用，0 表示停用")


class StatusPatchRequest(BaseModel):
    status: int = Field(title="状态", description="目标状态值，通常 1 表示启用，0 表示停用")


class DepartmentUpsertRequest(BaseModel):
    parentId: int | None = Field(default=None, title="上级部门 ID", description="父级部门 ID，顶级部门可为空")
    leaderId: int | None = Field(default=None, title="负责人 ID", description="部门负责人用户 ID，可为空")
    name: str = Field(min_length=1, max_length=50, title="部门名称", description="部门显示名称")
    code: str | None = Field(default=None, max_length=50, title="部门编码", description="部门唯一编码")
    phone: str | None = Field(default=None, max_length=20, title="联系电话", description="部门联系电话")
    email: str | None = Field(default=None, max_length=100, title="邮箱", description="部门联系邮箱")
    sort: int = Field(default=0, title="排序值", description="部门排序，值越小越靠前")
    description: str | None = Field(default=None, max_length=200, title="部门说明", description="部门备注说明")


class DictTypeUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50, title="字典名称", description="字典类型名称")
    code: str = Field(min_length=1, max_length=50, title="字典编码", description="字典类型唯一编码")
    description: str | None = Field(default=None, max_length=200, title="字典说明", description="字典类型备注说明")
    sort: int = Field(default=0, title="排序值", description="字典类型排序，值越小越靠前")
    status: int = Field(default=1, title="状态", description="字典类型状态，1 表示启用，0 表示停用")


class DictDataUpsertRequest(BaseModel):
    dictTypeId: int = Field(title="字典类型 ID", description="所属字典类型 ID")
    label: str = Field(min_length=1, max_length=50, title="字典标签", description="字典项显示文本")
    value: str = Field(min_length=1, max_length=50, title="字典值", description="字典项实际值")
    sort: int = Field(default=0, title="排序值", description="字典项排序，值越小越靠前")
    cssClass: str | None = Field(default=None, max_length=50, title="样式类名", description="前端样式类名")
    remark: str | None = Field(default=None, max_length=200, title="备注", description="字典项备注说明")
    status: int = Field(default=1, title="状态", description="字典项状态，1 表示启用，0 表示停用")


class DepartmentItem(BaseModel):
    id: int = Field(title="部门 ID", description="部门主键 ID")
    name: str = Field(title="部门名称", description="部门显示名称")
    code: str | None = Field(default=None, title="部门编码", description="部门唯一编码")
    parentId: int | None = Field(default=None, title="上级部门 ID", description="父级部门 ID")
    leaderId: int | None = Field(default=None, title="负责人 ID", description="部门负责人用户 ID")
    phone: str | None = Field(default=None, title="联系电话", description="部门联系电话")
    email: str | None = Field(default=None, title="邮箱", description="部门联系邮箱")
    sort: int = Field(title="排序值", description="部门排序，值越小越靠前")
    status: int = Field(title="状态", description="部门状态，1 表示启用，0 表示停用")
    description: str | None = Field(default=None, title="部门说明", description="部门备注说明")
    createdAt: str | None = Field(default=None, title="创建时间", description="部门创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="部门最后更新时间")
    children: list[DepartmentItem] = Field(default_factory=list, title="子部门列表", description="当前部门的子部门树")


class MenuItem(BaseModel):
    id: int = Field(title="菜单 ID", description="菜单主键 ID")
    parentId: int | None = Field(default=None, title="上级菜单 ID", description="父级菜单 ID")
    name: str | None = Field(default=None, title="路由名称", description="前端路由名称")
    title: str = Field(title="菜单标题", description="菜单或按钮显示名称")
    type: str = Field(title="菜单类型", description="菜单类型，可选值为 menu 或 button")
    path: str | None = Field(default=None, title="路由路径", description="前端访问路径")
    component: str | None = Field(default=None, title="组件路径", description="前端组件文件路径")
    permission: str | None = Field(default=None, title="权限标识", description="按钮或接口权限编码")
    icon: str | None = Field(default=None, title="图标", description="菜单图标标识")
    sort: int = Field(title="排序值", description="菜单排序，值越小越靠前")
    visible: int = Field(title="是否显示", description="菜单是否显示，1 显示，0 隐藏")
    status: int = Field(title="状态", description="菜单状态，1 表示启用，0 表示停用")
    createdAt: str | None = Field(default=None, title="创建时间", description="菜单创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="菜单最后更新时间")
    children: list[MenuItem] = Field(default_factory=list, title="子菜单列表", description="当前菜单的子菜单树")


class RoleSummary(BaseModel):
    id: int = Field(title="角色 ID", description="角色主键 ID")
    name: str = Field(title="角色名称", description="角色显示名称")
    code: str = Field(title="角色编码", description="角色唯一编码")
    description: str | None = Field(default=None, title="角色说明", description="角色备注说明")
    dataScope: int = Field(title="数据权限范围", description="角色的数据权限范围标记")
    sort: int = Field(title="排序值", description="角色排序，值越小越靠前")
    status: int = Field(title="状态", description="角色状态，1 表示启用，0 表示停用")
    createdAt: str | None = Field(default=None, title="创建时间", description="角色创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="角色最后更新时间")


class RoleMenuRelation(BaseModel):
    roleId: int = Field(title="角色 ID", description="角色主键 ID")
    menuId: int = Field(title="菜单 ID", description="菜单主键 ID")
    createdAt: str | None = Field(default=None, title="创建时间", description="关联创建时间")
    menu: MenuItem | None = Field(default=None, title="菜单信息", description="关联的菜单详情")


class RoleDepartmentRelation(BaseModel):
    roleId: int = Field(title="角色 ID", description="角色主键 ID")
    departmentId: int = Field(title="部门 ID", description="部门主键 ID")
    createdAt: str | None = Field(default=None, title="创建时间", description="关联创建时间")
    department: DepartmentItem | None = Field(default=None, title="部门信息", description="关联的部门详情")


class RoleDetail(RoleSummary):
    menus: list[RoleMenuRelation] = Field(default_factory=list, title="菜单权限列表", description="角色关联的菜单权限")
    departments: list[RoleDepartmentRelation] = Field(
        default_factory=list,
        title="部门权限列表",
        description="角色关联的数据权限部门",
    )


class UserRoleRelation(BaseModel):
    userId: int = Field(title="用户 ID", description="用户主键 ID")
    roleId: int = Field(title="角色 ID", description="角色主键 ID")
    createdAt: str | None = Field(default=None, title="创建时间", description="关联创建时间")
    role: RoleSummary | None = Field(default=None, title="角色信息", description="关联的角色详情")


class UserItem(BaseModel):
    id: int = Field(title="用户 ID", description="用户主键 ID")
    username: str = Field(title="用户名", description="登录用户名")
    nickname: str | None = Field(default=None, title="昵称", description="用户昵称")
    email: str | None = Field(default=None, title="邮箱", description="邮箱地址")
    phone: str | None = Field(default=None, title="手机号", description="联系电话")
    avatar: str | None = Field(default=None, title="头像地址", description="头像访问地址")
    avatarId: int | None = Field(default=None, title="头像文件 ID", description="头像文件记录 ID")
    avatarName: str | None = Field(default=None, title="头像文件名", description="头像原始文件名")
    departmentId: int | None = Field(default=None, title="部门 ID", description="所属部门 ID")
    gender: int = Field(title="性别", description="性别标记，0 未知，1 男，2 女")
    status: int = Field(title="状态", description="用户状态，1 表示启用，0 表示停用")
    createdAt: str | None = Field(default=None, title="创建时间", description="用户创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="用户最后更新时间")
    lastLoginAt: str | None = Field(default=None, title="最后登录时间", description="最近一次登录时间")
    department: DepartmentItem | None = Field(default=None, title="部门信息", description="所属部门详情")
    roles: list[UserRoleRelation] = Field(default_factory=list, title="角色列表", description="用户拥有的角色信息")


class DictTypeItem(BaseModel):
    id: int = Field(title="字典类型 ID", description="字典类型主键 ID")
    name: str = Field(title="字典名称", description="字典类型名称")
    code: str = Field(title="字典编码", description="字典类型唯一编码")
    description: str | None = Field(default=None, title="字典说明", description="字典类型备注说明")
    sort: int = Field(title="排序值", description="字典类型排序，值越小越靠前")
    status: int = Field(title="状态", description="字典类型状态，1 表示启用，0 表示停用")
    createdAt: str | None = Field(default=None, title="创建时间", description="字典类型创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="字典类型最后更新时间")


class DictDataItem(BaseModel):
    id: int = Field(title="字典数据 ID", description="字典数据主键 ID")
    dictTypeId: int = Field(title="字典类型 ID", description="所属字典类型 ID")
    label: str = Field(title="字典标签", description="字典项显示文本")
    value: str = Field(title="字典值", description="字典项实际值")
    sort: int = Field(title="排序值", description="字典项排序，值越小越靠前")
    cssClass: str | None = Field(default=None, title="样式类名", description="前端样式类名")
    remark: str | None = Field(default=None, title="备注", description="字典项备注说明")
    status: int = Field(title="状态", description="字典项状态，1 表示启用，0 表示停用")
    createdAt: str | None = Field(default=None, title="创建时间", description="字典项创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="字典项最后更新时间")


class FileRecordItem(BaseModel):
    id: int = Field(title="文件 ID", description="文件记录主键 ID")
    userId: int = Field(title="上传用户 ID", description="上传该文件的用户 ID")
    name: str = Field(title="文件名称", description="原始文件名称")
    originalName: str = Field(title="原始文件名", description="上传时的原始文件名")
    storedName: str = Field(title="存储文件名", description="对象存储中的文件路径")
    size: int = Field(title="文件大小", description="文件大小，单位为字节")
    mimeType: str = Field(title="媒体类型", description="文件 MIME 类型")
    bucketName: str = Field(title="存储桶名称", description="对象存储桶名称")
    bucketType: str = Field(title="存储分类", description="文件所属存储分类，例如 image 或 file")
    folder: str = Field(title="目录", description="对象存储中的目录名称")
    url: str = Field(title="访问地址", description="文件访问地址")
    status: int = Field(title="状态", description="文件状态，1 表示有效")
    createdAt: str | None = Field(default=None, title="创建时间", description="文件上传时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="文件记录最后更新时间")


class DocumentTaskItem(BaseModel):
    id: int = Field(title="任务 ID", description="文档处理任务主键 ID")
    documentId: int = Field(title="文档 ID", description="关联的文档 ID")
    taskType: str = Field(title="任务类型", description="任务类型，例如 ingest 或 reprocess")
    queueName: str = Field(title="队列名称", description="任务所在的消息队列名称")
    status: str = Field(title="任务状态", description="任务状态，例如 pending、processing、success、failed")
    attempts: int = Field(title="重试次数", description="当前任务已执行的尝试次数")
    errorMessage: str | None = Field(default=None, title="错误信息", description="任务失败时的错误说明")
    startedAt: str | None = Field(default=None, title="开始时间", description="任务开始处理时间")
    finishedAt: str | None = Field(default=None, title="完成时间", description="任务完成处理时间")
    createdAt: str | None = Field(default=None, title="创建时间", description="任务创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="任务最后更新时间")


class DocumentChunkItem(BaseModel):
    id: int = Field(title="切片 ID", description="文档切片主键 ID")
    documentId: int = Field(title="文档 ID", description="所属文档 ID")
    taskId: int | None = Field(default=None, title="任务 ID", description="生成该切片的任务 ID")
    chunkIndex: int = Field(title="切片序号", description="切片在文档中的顺序编号")
    content: str = Field(title="切片内容", description="切片文本内容")
    contentLength: int = Field(title="内容长度", description="切片文本字符长度")
    charStart: int = Field(title="起始字符位置", description="切片在原文中的起始字符位置")
    charEnd: int = Field(title="结束字符位置", description="切片在原文中的结束字符位置")
    status: str = Field(title="切片状态", description="切片状态，例如 ready")
    metadata: Any | None = Field(default=None, title="附加元数据", description="切片解析过程中生成的额外元数据")
    createdAt: str | None = Field(default=None, title="创建时间", description="切片创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="切片最后更新时间")


class DocumentItem(BaseModel):
    id: int = Field(title="文档 ID", description="文档主键 ID")
    userId: int = Field(title="上传用户 ID", description="上传该文档的用户 ID")
    fileId: int = Field(title="文件 ID", description="关联的文件记录 ID")
    title: str = Field(title="文档标题", description="文档标题")
    fileName: str = Field(title="文件名称", description="原始文件名称")
    mimeType: str = Field(title="媒体类型", description="文件 MIME 类型")
    fileSize: int = Field(title="文件大小", description="文件大小，单位为字节")
    status: str = Field(title="文档状态", description="文档处理状态，例如 pending、processing、success、failed")
    parseMode: str = Field(title="解析模式", description="文档解析模式，例如 auto")
    textLength: int | None = Field(default=None, title="文本长度", description="抽取后的文本总长度")
    chunkCount: int | None = Field(default=None, title="切片数量", description="已生成的切片总数")
    errorMessage: str | None = Field(default=None, title="错误信息", description="处理失败时的错误说明")
    processedAt: str | None = Field(default=None, title="处理完成时间", description="文档处理完成时间")
    createdAt: str | None = Field(default=None, title="创建时间", description="文档创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="文档最后更新时间")
    file: FileRecordItem | None = Field(default=None, title="文件信息", description="关联的文件详情")
    tasks: list[DocumentTaskItem] = Field(default_factory=list, title="任务列表", description="文档关联的处理任务列表")
    chunks: list[DocumentChunkItem] = Field(default_factory=list, title="切片列表", description="文档关联的切片列表")


class CaptchaData(BaseModel):
    captchaId: str = Field(title="验证码 ID", description="验证码唯一标识，用于后续登录校验")
    captchaSvg: str = Field(title="验证码 SVG", description="验证码图片的 SVG 内容")


class LoginData(BaseModel):
    access_token: str = Field(title="访问令牌", description="登录成功后返回的 Bearer Token")
    token_type: str = Field(title="令牌类型", description="令牌类型，固定为 bearer")
    user: UserItem = Field(title="用户信息", description="当前登录用户的详细信息")


class DocumentQueueStatusData(BaseModel):
    queueName: str = Field(title="队列名称", description="文档处理队列名称")
    processingMode: str = Field(title="处理模式", description="文档处理模式，例如 inline 或 worker")
    pendingCount: int = Field(title="待处理数量", description="队列中待处理任务数量")
    processingCount: int = Field(title="处理中数量", description="当前正在处理的任务数量")


class DocumentSearchHit(BaseModel):
    score: float = Field(title="综合分数", description="向量召回与关键词补偿混合后的综合排序分数")
    vectorScore: float | None = Field(default=None, title="向量分数", description="向量召回得到的原始分数")
    keywordScore: float | None = Field(default=None, title="关键词分数", description="关键词匹配得到的补充分数")
    chunkId: int = Field(title="切片 ID", description="命中的切片 ID")
    documentId: int = Field(title="文档 ID", description="命中的文档 ID")
    chunkIndex: int = Field(title="切片序号", description="命中的切片序号")
    content: str = Field(title="切片内容", description="命中的切片文本内容")
    document: DocumentItem | None = Field(default=None, title="文档信息", description="命中文档的概要信息")


class ReprocessDocumentData(BaseModel):
    document: DocumentItem = Field(title="文档信息", description="重新入队后的文档详情")
    task: DocumentTaskItem = Field(title="任务信息", description="本次重新处理对应的任务信息")


class ChatMessage(BaseModel):
    role: str = Field(title="角色", description="消息角色: user 或 assistant")
    content: str = Field(title="内容", description="消息文本内容")


class DocumentQaRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000, title="问题", description="用户发起的检索问答问题")
    limit: int = Field(default=4, ge=1, le=10, title="命中数量", description="问答前召回的切片数量")
    documentIds: list[int] | None = Field(default=None, title="文档 ID 列表", description="限定在多份文档内进行问答，为空则检索全部可见文档")
    history: list[ChatMessage] = Field(default_factory=list, title="对话历史", description="本轮之前的对话历史，用于多轮上下文")


class DocumentQaSourceItem(BaseModel):
    documentId: int | None = Field(default=None, title="文档 ID", description="命中来源文档 ID")
    documentTitle: str | None = Field(default=None, title="文档标题", description="命中来源文档标题")
    chunkId: int | None = Field(default=None, title="切片 ID", description="命中的切片 ID")
    chunkIndex: int | None = Field(default=None, title="切片序号", description="命中的切片序号")
    score: float | None = Field(default=None, title="综合分数", description="切片综合排序分数")
    content: str | None = Field(default=None, title="切片内容", description="切片原始内容")


class DocumentQaData(BaseModel):
    question: str = Field(title="问题", description="用户发起的原始问题")
    answer: str = Field(title="答案", description="基于检索结果生成的预览答案")
    answerMode: str = Field(title="回答模式", description="当前回答生成模式")
    answerModel: str | None = Field(default=None, title="回答模型", description="当前用于生成回答的模型名称")
    retrievalCount: int = Field(default=0, title="命中数量", description="本次问答引用的切片数量")
    sources: list[DocumentQaSourceItem] = Field(default_factory=list, title="来源切片", description="本次回答参考的切片列表")
    suggestions: list[str] = Field(default_factory=list, title="追问建议", description="基于当前对话自动生成的 3 个追问建议")


class DocumentQaMessageItem(BaseModel):
    id: int = Field(title="消息 ID", description="聊天消息主键 ID")
    role: str = Field(title="角色", description="消息角色: user 或 assistant")
    content: str = Field(title="内容", description="消息文本内容")
    timestamp: str | None = Field(default=None, title="消息时间", description="消息时间")
    answerMode: str | None = Field(default=None, title="回答模式", description="助手消息的回答模式")
    answerModel: str | None = Field(default=None, title="回答模型", description="助手消息使用的模型名称")
    sources: list[DocumentQaSourceItem] = Field(default_factory=list, title="引用来源", description="助手消息引用来源")
    suggestions: list[str] = Field(default_factory=list, title="追问建议", description="助手消息附带的追问建议")


class DocumentQaSessionItem(BaseModel):
    id: int = Field(title="会话 ID", description="聊天会话主键 ID")
    title: str | None = Field(default=None, title="会话标题", description="会话标题")
    createdAt: str | None = Field(default=None, title="创建时间", description="会话创建时间")
    updatedAt: str | None = Field(default=None, title="更新时间", description="会话更新时间")
    docIds: list[int] = Field(default_factory=list, title="文档范围", description="当前会话限定的文档 ID 列表")
    messages: list[DocumentQaMessageItem] = Field(default_factory=list, title="消息列表", description="当前会话的全部消息")


class DocumentQaSessionCreateRequest(BaseModel):
    docIds: list[int] = Field(default_factory=list, title="文档范围", description="当前会话限定的文档 ID 列表")


class DocumentQaSessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255, title="会话标题", description="更新后的会话标题")
    docIds: list[int] = Field(default_factory=list, title="文档范围", description="当前会话限定的文档 ID 列表")


class DocumentQaMessageCreateRequest(BaseModel):
    role: str = Field(title="角色", description="消息角色: user 或 assistant")
    content: str = Field(title="内容", description="消息文本内容")
    timestamp: str | int | None = Field(default=None, title="消息时间", description="前端传入的消息时间")
    answerMode: str | None = Field(default=None, max_length=50, title="回答模式", description="助手消息的回答模式")
    answerModel: str | None = Field(default=None, max_length=100, title="回答模型", description="助手消息使用的模型名称")
    sources: list[DocumentQaSourceItem] = Field(default_factory=list, title="引用来源", description="助手消息引用来源")
    suggestions: list[str] = Field(default_factory=list, title="追问建议", description="助手消息附带的追问建议")


class DocumentQaSessionSyncRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255, title="会话标题", description="会话标题")
    docIds: list[int] = Field(default_factory=list, title="文档范围", description="当前会话限定的文档 ID 列表")
    messages: list[DocumentQaMessageCreateRequest] = Field(default_factory=list, title="消息列表", description="当前会话全部消息")


class FollowUpRequest(BaseModel):
    question: str = Field(title="用户问题", description="用户最近一次提问的内容")
    answer: str = Field(title="助手回答", description="助手对最近问题的回答内容")


class UploadFileResult(FileRecordItem):
    document: DocumentItem | None = Field(default=None, title="文档信息", description="关联生成的文档信息")
    documentId: int | None = Field(default=None, title="文档 ID", description="关联生成的文档 ID")
    documentStatus: str | None = Field(default=None, title="文档状态", description="关联文档当前的处理状态")


DepartmentItem.model_rebuild()
MenuItem.model_rebuild()
