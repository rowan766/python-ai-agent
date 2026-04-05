# 企业级 RAG 前后端接口设计草案

## 1. 文档目标

本文件承接以下两份方案文档：

- 《企业级 RAG 知识库执行方案》
- 《企业级 RAG 数据库表设计草案》

目标：

- 明确企业级 RAG 平台的前后端接口边界
- 明确每类页面需要哪些接口支撑
- 明确权限边界、审批流边界和检索边界
- 为后续前端开发和后端编码提供统一契约

本文件不写具体实现代码，只做接口层方案设计。

---

## 2. 总体接口设计原则

### 2.1 按领域分组，而不是按技术模块分组

建议 API 分组按业务域划分：

- `auth`
- `users`
- `departments`
- `department-requests`
- `roles`
- `knowledge-bases`
- `documents`
- `document-shares`
- `rag`
- `approvals`
- `audit`
- `admin`

这样前端页面与后端能力更容易对齐。

### 2.2 业务接口与调试接口分离

当前项目已有一些调试型接口，例如 embedding / chat 健康检查。

建议后续分成两类：

- 正式业务接口：用于页面与业务流程
- 调试接口：用于排查模型、向量库、系统状态

正式环境中，调试接口通常应受限，仅管理员可用。

### 2.3 权限校验前置

每个接口应先判断：

- 当前用户是谁
- 当前用户属于哪些部门
- 当前用户拥有哪些角色
- 当前用户是否有访问当前资源的范围权限

不允许把权限判断完全交给前端。

### 2.4 检索接口只返回有权限的结果

企业级 RAG 的核心原则是：

后端检索接口只能返回用户有权访问的知识结果，不允许前端自行过滤。

---

## 3. 前端主页面与接口映射

建议前端信息架构分为 7 个区域：

### 3.1 认证与组织入口

页面：

- 登录页
- 注册页
- 首次进入页
- 申请加入部门页
- 申请状态页

对应接口：

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/users/me/profile`
- `GET /api/departments/tree`
- `POST /api/department-requests`
- `GET /api/department-requests/my`

### 3.2 工作台

页面：

- 我的部门
- 我的知识库
- 最近上传
- 待审批
- 最近检索
- 我的快捷入口

对应接口：

- `GET /api/users/me/dashboard`
- `GET /api/users/me/memberships`
- `GET /api/knowledge-bases/my`
- `GET /api/documents/my/recent`
- `GET /api/approvals/my/pending`
- `GET /api/rag/my/recent-searches`

### 3.3 部门与组织管理

页面：

- 部门树
- 部门详情
- 部门成员管理
- 部门角色管理

对应接口：

- `GET /api/departments/tree`
- `GET /api/departments/{departmentId}`
- `GET /api/departments/{departmentId}/members`
- `POST /api/departments`
- `PATCH /api/departments/{departmentId}`
- `POST /api/departments/{departmentId}/members`
- `PATCH /api/departments/{departmentId}/members/{membershipId}`

### 3.4 知识库空间

页面：

- 知识库列表
- 知识库详情
- 知识库成员
- 知识库策略

对应接口：

- `GET /api/knowledge-bases`
- `POST /api/knowledge-bases`
- `GET /api/knowledge-bases/{knowledgeBaseId}`
- `PATCH /api/knowledge-bases/{knowledgeBaseId}`
- `GET /api/knowledge-bases/{knowledgeBaseId}/members`
- `PATCH /api/knowledge-bases/{knowledgeBaseId}/policies`

### 3.5 文档治理

页面：

- 文档上传
- 文档列表
- 文档详情
- 文档版本
- 文档共享设置
- 文档审核与发布

对应接口：

- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/{documentId}`
- `PATCH /api/documents/{documentId}`
- `GET /api/documents/{documentId}/versions`
- `POST /api/documents/{documentId}/versions`
- `GET /api/documents/{documentId}/shares`
- `POST /api/documents/{documentId}/shares`
- `POST /api/documents/{documentId}/publish`
- `POST /api/documents/{documentId}/archive`

### 3.6 审批中心

页面：

- 我的待审批
- 我发起的审批
- 部门加入审批
- 文档发布审批
- 文档共享审批

对应接口：

- `GET /api/approvals/pending`
- `GET /api/approvals/created-by-me`
- `GET /api/approvals/{approvalId}`
- `POST /api/approvals/{approvalId}/approve`
- `POST /api/approvals/{approvalId}/reject`

### 3.7 智能问答与检索

页面：

- 问答页
- 检索结果页
- 引用来源面板
- 历史检索记录

对应接口：

- `POST /api/rag/search`
- `POST /api/rag/ask`
- `GET /api/rag/sources/{searchId}`
- `GET /api/rag/my/recent-searches`

---

## 4. 接口分组设计

## 4.1 auth

作用：

- 账号认证

建议接口：

### `POST /api/auth/register`

作用：

- 用户注册

请求：

- `email`
- `username`
- `password`

响应：

- `access_token`
- `user`
- `profile_status`

说明：

- 注册成功后用户默认处于“无部门归属”状态

### `POST /api/auth/login`

作用：

- 用户登录

响应建议：

- `access_token`
- `user`
- `memberships`
- `default_department`

### `GET /api/auth/me`

作用：

- 获取当前登录用户基础信息

建议返回：

- 基础账号信息
- 当前组织归属摘要
- 当前角色摘要

---

## 4.2 users

作用：

- 个人中心、工作台

建议接口：

### `GET /api/users/me/profile`

返回：

- 个人资料
- 当前组织状态
- 主部门
- 可访问知识库数量

### `PATCH /api/users/me/profile`

作用：

- 编辑个人资料

### `GET /api/users/me/memberships`

作用：

- 查看当前用户部门归属列表

### `GET /api/users/me/dashboard`

作用：

- 获取工作台聚合数据

建议返回：

- 部门摘要
- 待审批数
- 最近上传
- 最近访问知识库
- 最近检索历史

---

## 4.3 departments

作用：

- 组织管理

建议接口：

### `GET /api/departments/tree`

作用：

- 获取部门树

前端用途：

- 申请加入部门选择器
- 管理后台部门树
- 知识库筛选

### `GET /api/departments/{departmentId}`

作用：

- 获取部门详情

建议返回：

- 基础信息
- 上下级关系摘要
- 成员统计
- 知识库数量

### `GET /api/departments/{departmentId}/members`

作用：

- 获取部门成员列表

### `POST /api/departments`

作用：

- 新建部门

权限：

- 平台管理员 / 有权限的组织管理员

### `PATCH /api/departments/{departmentId}`

作用：

- 修改部门信息

---

## 4.4 department-requests

作用：

- 管理加入部门流程

建议接口：

### `POST /api/department-requests`

作用：

- 用户发起加入部门申请

请求：

- `target_department_id`
- `requested_role_code`
- `reason`

### `GET /api/department-requests/my`

作用：

- 查看我发起的申请

### `GET /api/department-requests/pending`

作用：

- 查看当前用户可审批的待审申请

### `POST /api/department-requests/{requestId}/approve`

作用：

- 审批通过

效果：

- 创建或激活 `department_membership`

### `POST /api/department-requests/{requestId}/reject`

作用：

- 驳回申请

---

## 4.5 roles

作用：

- 角色与权限管理

建议接口：

### `GET /api/roles`

作用：

- 获取角色列表

### `GET /api/roles/{roleId}`

作用：

- 获取角色详情与权限点

### `POST /api/users/{userId}/roles`

作用：

- 给用户赋予某个范围内角色

请求建议：

- `role_code`
- `scope_type`
- `scope_id`

### `DELETE /api/users/{userId}/roles/{userRoleId}`

作用：

- 回收角色

---

## 4.6 knowledge-bases

作用：

- 知识库空间管理

建议接口：

### `GET /api/knowledge-bases`

作用：

- 获取当前用户可访问的知识库列表

支持筛选：

- 部门
- 状态
- 是否我创建
- 是否我管理

### `GET /api/knowledge-bases/my`

作用：

- 获取当前用户直接关联或常用的知识库

### `POST /api/knowledge-bases`

作用：

- 创建知识库空间

请求建议：

- `department_id`
- `name`
- `description`
- `default_visibility`
- `require_publish_approval`

### `GET /api/knowledge-bases/{knowledgeBaseId}`

作用：

- 获取知识库空间详情

### `PATCH /api/knowledge-bases/{knowledgeBaseId}`

作用：

- 修改知识库配置

### `GET /api/knowledge-bases/{knowledgeBaseId}/members`

作用：

- 查看知识库成员

### `PATCH /api/knowledge-bases/{knowledgeBaseId}/policies`

作用：

- 修改知识库默认策略

---

## 4.7 documents

作用：

- 文档治理与版本管理

建议接口：

### `POST /api/documents/upload`

作用：

- 上传文档并归属到知识库

请求建议：

- `file`
- `knowledge_base_id`
- `title`
- `description`
- `visibility_level`
- `share_policy`
- `tags`

响应建议：

- `document_id`
- `version_id`
- `status`
- `chunks_count`
- `requires_approval`

说明：

- 这里不建议再沿用“无业务归属的直接上传”
- 应要求明确归属到某个知识库空间

### `GET /api/documents`

作用：

- 获取当前用户可见文档列表

支持筛选：

- `knowledge_base_id`
- `department_id`
- `status`
- `visibility_level`
- `keyword`
- `uploaded_by`

### `GET /api/documents/{documentId}`

作用：

- 获取文档详情

建议返回：

- 基础信息
- 当前状态
- 当前版本
- 可见性
- 共享策略
- 上传人
- 审批状态

### `PATCH /api/documents/{documentId}`

作用：

- 更新文档元信息

### `GET /api/documents/{documentId}/versions`

作用：

- 获取版本列表

### `POST /api/documents/{documentId}/versions`

作用：

- 上传新版本

### `POST /api/documents/{documentId}/publish`

作用：

- 触发发布或发布审批

### `POST /api/documents/{documentId}/archive`

作用：

- 归档文档

### `POST /api/documents/{documentId}/disable`

作用：

- 禁止进入检索或停用文档

---

## 4.8 document-shares

作用：

- 管理文档共享策略

建议接口：

### `GET /api/documents/{documentId}/shares`

作用：

- 查看当前文档共享配置

### `POST /api/documents/{documentId}/shares`

作用：

- 新建共享策略

请求建议：

- `share_type`
- `target_department_ids`
- `target_role_codes`
- `allow_search`
- `allow_view`
- `allow_download`

### `PATCH /api/documents/{documentId}/shares/{shareId}`

作用：

- 修改共享策略

### `DELETE /api/documents/{documentId}/shares/{shareId}`

作用：

- 撤销共享策略

说明：

- 如果当前知识库策略要求审批，则该操作应创建审批单而不是立即生效

---

## 4.9 approvals

作用：

- 统一审批中心

建议接口：

### `GET /api/approvals/pending`

作用：

- 获取当前用户的待审批列表

支持筛选：

- `request_type`
- `status`
- `department_id`

### `GET /api/approvals/created-by-me`

作用：

- 获取我发起的审批单

### `GET /api/approvals/{approvalId}`

作用：

- 获取审批详情

### `POST /api/approvals/{approvalId}/approve`

请求建议：

- `comment`

### `POST /api/approvals/{approvalId}/reject`

请求建议：

- `comment`

### `POST /api/approvals/{approvalId}/cancel`

作用：

- 发起人取消审批

---

## 4.10 rag

作用：

- 企业级检索与问答

建议接口：

### `POST /api/rag/search`

作用：

- 执行权限内检索

请求建议：

- `query`
- `knowledge_base_ids`
- `department_ids`
- `top_k`
- `search_mode`

说明：

- 用户传入的范围只是“意图范围”
- 真正可搜索范围必须由后端再次裁剪

响应建议：

- `search_id`
- `query`
- `results`
- `effective_scope`
- `retrieval_mode`

每条结果建议返回：

- `document_id`
- `document_title`
- `knowledge_base_id`
- `knowledge_base_name`
- `department_id`
- `department_name`
- `chunk_content`
- `score`
- `visibility_level`

### `POST /api/rag/ask`

作用：

- 在权限内完成检索增强问答

请求建议：

- `query`
- `knowledge_base_ids`
- `department_ids`
- `conversation_id`
- `include_sources`

响应建议：

- `answer`
- `sources`
- `search_id`
- `effective_scope`

### `GET /api/rag/sources/{searchId}`

作用：

- 查看本次问答或检索的引用来源

### `GET /api/rag/my/recent-searches`

作用：

- 获取当前用户最近检索记录

---

## 4.11 audit

作用：

- 审计与治理

建议接口：

### `GET /api/audit/logs`

作用：

- 查询审计日志

支持筛选：

- 用户
- 部门
- 资源类型
- 时间范围

### `GET /api/audit/search-logs`

作用：

- 查询检索日志

### `GET /api/audit/document-access-logs`

作用：

- 查询文档访问日志

权限：

- 审计员 / 安全管理员 / 平台管理员

---

## 4.12 admin

作用：

- 平台级配置

建议接口：

### `GET /api/admin/system-overview`

作用：

- 获取平台运行概览

### `GET /api/admin/departments/overview`

作用：

- 获取部门与知识库概况

### `GET /api/admin/models/health`

作用：

- 查看模型、embedding、向量库状态

说明：

- 当前项目已有 debug 方向接口，可逐步归入这一层

---

## 5. 关键前端流程设计

## 5.1 注册并加入部门

流程建议：

1. 用户注册
2. 登录成功
3. 跳转“完善身份 / 申请加入部门”
4. 获取部门树
5. 选择部门并提交申请
6. 查看申请状态
7. 审批通过后进入工作台

前端关键页面：

- 注册页
- 申请页
- 等待审批页

后端关键接口：

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/departments/tree`
- `POST /api/department-requests`
- `GET /api/department-requests/my`

---

## 5.2 部门负责人审批加入申请

流程建议：

1. 负责人进入待审批中心
2. 查看部门加入申请
3. 审批通过或拒绝
4. 系统更新成员关系

后端关键接口：

- `GET /api/department-requests/pending`
- `POST /api/department-requests/{requestId}/approve`
- `POST /api/department-requests/{requestId}/reject`

---

## 5.3 创建知识库空间

流程建议：

1. 部门管理员进入知识库管理
2. 创建知识库空间
3. 设置默认可见性、审批策略、共享策略
4. 指定知识库成员

后端关键接口：

- `POST /api/knowledge-bases`
- `PATCH /api/knowledge-bases/{knowledgeBaseId}`
- `PATCH /api/knowledge-bases/{knowledgeBaseId}/policies`

---

## 5.4 上传文档并治理

流程建议：

1. 用户进入某个知识库空间
2. 选择上传文件
3. 设置标题、描述、可见性、标签
4. 上传完成后进入草稿或待审状态
5. 审批通过后正式进入检索

后端关键接口：

- `POST /api/documents/upload`
- `GET /api/documents/{documentId}`
- `POST /api/documents/{documentId}/publish`

建议前端在上传后显示：

- 切片数量
- 当前状态
- 是否进入检索
- 是否触发审批

---

## 5.5 设置共享策略

流程建议：

1. 文档负责人进入共享设置页
2. 选择共享方式
3. 选择目标部门或目标角色
4. 提交
5. 如需审批则进入审批流

后端关键接口：

- `GET /api/documents/{documentId}/shares`
- `POST /api/documents/{documentId}/shares`
- `PATCH /api/documents/{documentId}/shares/{shareId}`

---

## 5.6 上级查看下属部门知识库

流程建议：

1. 上级用户进入知识库首页
2. 默认可见范围为“本部门及下级部门”
3. 可按部门树筛选
4. 打开下属部门知识库与文档

后端关键接口：

- `GET /api/knowledge-bases`
- `GET /api/documents`
- `POST /api/rag/search`

说明：

- 后端必须自动限制在用户真实可见组织范围内

---

## 5.7 企业级问答

流程建议：

1. 用户进入问答页
2. 选择知识库范围或部门范围
3. 输入问题
4. 后端执行权限内检索
5. 前端展示答案与引用来源
6. 用户点击来源查看原文片段

后端关键接口：

- `POST /api/rag/ask`
- `GET /api/rag/sources/{searchId}`

前端必须展示：

- 答案
- 来源文档
- 来源部门
- 来源知识库
- 命中片段

---

## 6. 推荐请求与响应风格

### 6.1 统一分页风格

列表接口建议统一返回：

- `items`
- `page`
- `page_size`
- `total`

### 6.2 统一状态字段

接口响应建议保留统一状态表达：

- `status`
- `message`
- `data`

或保持 REST 风格但错误统一：

- `detail`
- `code`

关键是全项目统一。

### 6.3 统一权限错误语义

建议区分：

- `401`：未登录 / token 无效
- `403`：已登录但无权限
- `404`：资源不存在或对当前用户不可见

### 6.4 问答接口返回引用

不要只返回大模型答案，至少应返回：

- `answer`
- `sources`
- `retrieval_mode`
- `effective_scope`

---

## 7. 当前项目升级路径建议

结合当前项目现状，建议接口演进按以下顺序推进：

### 第一阶段

补齐组织与身份接口：

- `departments`
- `department-requests`
- `users/me/memberships`

### 第二阶段

引入知识库空间接口：

- `knowledge-bases`

### 第三阶段

重构上传接口为知识库归属型上传：

- 用 `documents/upload` 替代纯 `/rag/upload`

### 第四阶段

将检索接口从“裸查询”升级为“权限过滤检索”：

- `rag/search`
- `rag/ask`

### 第五阶段

补齐审批与审计接口：

- `approvals`
- `audit`

---

## 8. MVP 最小接口集合

如果只做第一版可用企业版，建议最小集合如下：

### 认证

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

### 组织

- `GET /api/departments/tree`
- `POST /api/department-requests`
- `GET /api/department-requests/my`
- `GET /api/department-requests/pending`
- `POST /api/department-requests/{requestId}/approve`
- `POST /api/department-requests/{requestId}/reject`

### 知识库

- `GET /api/knowledge-bases`
- `POST /api/knowledge-bases`
- `GET /api/knowledge-bases/{knowledgeBaseId}`

### 文档

- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/{documentId}`
- `POST /api/documents/{documentId}/publish`

### 共享

- `GET /api/documents/{documentId}/shares`
- `POST /api/documents/{documentId}/shares`

### 检索

- `POST /api/rag/search`
- `POST /api/rag/ask`

### 审批

- `GET /api/approvals/pending`
- `POST /api/approvals/{approvalId}/approve`
- `POST /api/approvals/{approvalId}/reject`

---

## 9. 设计结论

对于企业级 RAG 平台，接口设计最重要的不是“接口数量多”，而是：

- 页面与业务域强对齐
- 权限边界明确
- 组织范围清晰
- 文档与知识空间归属稳定
- 检索天然带权限过滤
- 审批与审计形成闭环

一句话总结：

`先把企业知识治理流程接口化，再把问答能力产品化。`

---

## 10. 下一步建议

建议接下来继续补第四份文档：

《企业级 RAG 前端页面信息架构草案》

重点可包括：

- 登录 / 申请 / 工作台 / 知识库 / 文档中心 / 审批中心 / 问答页 的页面结构
- 页面间跳转关系
- 每个页面的核心模块与交互流程
- 哪些页面是普通成员看到的，哪些页面是负责人/管理员看到的

这样你后续做前端会更顺，也更容易和这三份后端方案对齐。
