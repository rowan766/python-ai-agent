# 企业级 RAG 数据库表设计草案

## 1. 文档目标

本文件用于承接《企业级 RAG 知识库执行方案》，给出一套适合当前项目逐步演进的数据库设计草案。

目标：

- 支撑企业级组织结构
- 支撑成员归属、审批、权限、共享
- 支撑知识库空间与文档治理
- 支撑权限过滤式 RAG 检索
- 支撑后续审计、统计、版本管理

本草案强调：

- 先完成稳定的数据边界
- 再做接口与前端页面
- 尽量避免未来大幅拆表重构

---

## 2. 总体建模原则

### 2.1 不把组织关系直接写死在用户表

不建议只在 `users` 表里放一个 `department_id`，因为企业场景常见：

- 一人多部门
- 主部门与协作部门并存
- 临时借调
- 历史归属保留

因此建议：

- `users` 只描述账号本身
- 部门归属通过 `department_memberships` 单独建模

### 2.2 不把权限只做成角色名

权限不应只依赖角色名，而应拆成：

- 角色
- 组织范围
- 资源策略

数据库层需要为这三部分留出扩展空间。

### 2.3 不把文档直接绑定到用户

推荐关系：

`部门 -> 知识库空间 -> 文档 -> 文档版本 -> 文档切片 -> 向量索引`

原因：

- 企业里“知识库空间”是管理单元
- 文档是空间里的资产
- 用户只是上传者或管理者，不应该成为知识归属主体

### 2.4 向量数据库不是唯一事实源

Qdrant 负责向量检索，但 PostgreSQL 才是业务事实源。

因此建议：

- PostgreSQL 保存完整业务状态
- Qdrant 保存切片向量与必要检索过滤字段
- 任何权限判定都以 PostgreSQL 业务模型为准

---

## 3. 分层表设计总览

建议按以下分层建设：

### 3.1 账号与身份层

- `users`
- `user_profiles`
- `roles`
- `permissions`
- `role_permissions`
- `user_roles`

### 3.2 组织层

- `departments`
- `department_closure` 或 `department_paths`
- `department_memberships`
- `department_join_requests`

### 3.3 知识空间层

- `knowledge_bases`
- `knowledge_base_members`
- `knowledge_base_policies`

### 3.4 文档治理层

- `documents`
- `document_versions`
- `document_files`
- `document_chunks`
- `document_tags`
- `tag_definitions`

### 3.5 共享与授权层

- `document_shares`
- `knowledge_base_shares`
- `resource_access_policies`

### 3.6 审批与工作流层

- `approval_requests`
- `approval_steps`
- `approval_records`

### 3.7 检索与审计层

- `search_sessions`
- `search_logs`
- `document_access_logs`
- `audit_logs`

---

## 4. 核心表设计

## 4.1 users

作用：

- 存储账号主信息

建议字段：

- `id`
- `email`
- `username`
- `hashed_password`
- `phone`
- `is_active`
- `is_locked`
- `last_login_at`
- `created_at`
- `updated_at`

说明：

- 只放认证相关基础信息
- 不直接放部门归属
- 不直接放知识库权限

建议唯一索引：

- `email`
- `username`

---

## 4.2 user_profiles

作用：

- 存储账号扩展资料

建议字段：

- `id`
- `user_id`
- `real_name`
- `avatar_url`
- `employee_no`
- `title`
- `location`
- `bio`
- `created_at`
- `updated_at`

说明：

- 认证信息与资料信息分离，后续扩展更稳

---

## 4.3 roles

作用：

- 定义角色

建议字段：

- `id`
- `code`
- `name`
- `scope_type`
- `description`
- `is_system`
- `created_at`

建议示例：

- `platform_admin`
- `security_admin`
- `department_director`
- `department_manager`
- `department_member`
- `knowledge_admin`
- `knowledge_operator`
- `knowledge_reviewer`
- `auditor`

说明：

- `scope_type` 可区分平台级、部门级、知识库级角色

---

## 4.4 permissions

作用：

- 定义原子权限点

建议字段：

- `id`
- `code`
- `name`
- `module`
- `description`

建议权限示例：

- `department.join.apply`
- `department.join.approve`
- `knowledge_base.create`
- `document.upload`
- `document.publish`
- `document.share`
- `document.delete`
- `search.global`
- `audit.view`

说明：

- 权限点应稳定、可枚举

---

## 4.5 role_permissions

作用：

- 建立角色与权限的多对多关系

建议字段：

- `id`
- `role_id`
- `permission_id`

建议唯一约束：

- `(role_id, permission_id)`

---

## 4.6 user_roles

作用：

- 赋予用户角色

建议字段：

- `id`
- `user_id`
- `role_id`
- `scope_type`
- `scope_id`
- `granted_by`
- `granted_at`
- `expires_at`
- `status`

说明：

- `scope_type + scope_id` 非常重要
- 角色不一定全局生效，可能只在某个部门或某个知识库内生效

示例：

- 某用户在平台是普通用户
- 但在“研发中心”是 `department_manager`
- 在“研发规范库”里又是 `knowledge_reviewer`

---

## 4.7 departments

作用：

- 定义企业组织节点

建议字段：

- `id`
- `parent_id`
- `code`
- `name`
- `full_name`
- `level`
- `path`
- `manager_user_id`
- `status`
- `created_at`
- `updated_at`

说明：

- `path` 可用于快速实现上下级范围查询
- `manager_user_id` 可作为默认负责人

建议索引：

- `parent_id`
- `code`
- `path`

---

## 4.8 department_closure 或 department_paths

作用：

- 支撑高效树结构查询

两种常见方式：

- `path` 路径字段
- 闭包表 `department_closure`

如果采用闭包表，建议字段：

- `ancestor_id`
- `descendant_id`
- `depth`

用途：

- 查某部门所有下级部门
- 查某用户的组织可见范围
- 查上级审批范围

如果组织树规模较大，闭包表通常更稳。

---

## 4.9 department_memberships

作用：

- 建模用户与部门的归属关系

建议字段：

- `id`
- `user_id`
- `department_id`
- `membership_type`
- `is_primary`
- `job_title`
- `status`
- `joined_at`
- `left_at`
- `approved_by`
- `created_at`
- `updated_at`

说明：

- `membership_type` 可区分主部门、协作部门、借调
- `status` 可支持待生效、有效、停用、历史

建议唯一约束：

- 对有效关系限制 `(user_id, department_id, membership_type)` 唯一

---

## 4.10 department_join_requests

作用：

- 记录用户申请加入部门的流程

建议字段：

- `id`
- `user_id`
- `target_department_id`
- `requested_role_code`
- `reason`
- `status`
- `reviewer_user_id`
- `review_comment`
- `submitted_at`
- `reviewed_at`
- `created_at`

建议状态：

- `pending`
- `approved`
- `rejected`
- `cancelled`

说明：

- 不建议审批信息直接写回 membership
- 申请表与成员关系表职责分离

---

## 4.11 knowledge_bases

作用：

- 表示知识库空间

建议字段：

- `id`
- `department_id`
- `code`
- `name`
- `description`
- `status`
- `default_visibility`
- `allow_upload`
- `require_publish_approval`
- `allow_cross_department_share`
- `created_by`
- `created_at`
- `updated_at`

建议状态：

- `draft`
- `active`
- `archived`
- `disabled`

说明：

- 一个部门可以有多个知识库空间
- 未来权限、统计、问答范围都应优先绑定到知识库空间

---

## 4.12 knowledge_base_members

作用：

- 建模知识库空间成员关系

建议字段：

- `id`
- `knowledge_base_id`
- `user_id`
- `role_code`
- `status`
- `joined_at`
- `granted_by`

说明：

- 不是所有部门成员都自动拥有同等知识库权限
- 可实现更细的知识空间内治理

---

## 4.13 knowledge_base_policies

作用：

- 存储知识库默认策略

建议字段：

- `id`
- `knowledge_base_id`
- `policy_type`
- `policy_value`
- `created_at`
- `updated_at`

示例：

- 默认文档可见性
- 是否允许上传即发布
- 是否必须审批共享
- 是否允许跨部门搜索

说明：

- 如果策略复杂，单独建策略表比全部堆到主表更稳

---

## 4.14 documents

作用：

- 表示业务文档实体

建议字段：

- `id`
- `knowledge_base_id`
- `department_id`
- `title`
- `description`
- `doc_type`
- `status`
- `visibility_level`
- `owner_user_id`
- `uploaded_by`
- `current_version_id`
- `is_search_enabled`
- `confidential_level`
- `source_type`
- `created_at`
- `updated_at`

建议状态：

- `draft`
- `pending_review`
- `published`
- `archived`
- `disabled`

说明：

- 文档状态不要省略
- 文档是否进入检索必须与状态挂钩

---

## 4.15 document_versions

作用：

- 管理文档版本

建议字段：

- `id`
- `document_id`
- `version_no`
- `storage_file_id`
- `change_summary`
- `status`
- `uploaded_by`
- `approved_by`
- `approved_at`
- `created_at`

说明：

- 企业文档治理几乎一定需要版本管理
- 当前版本可在 `documents.current_version_id` 指向

---

## 4.16 document_files

作用：

- 保存物理文件信息

建议字段：

- `id`
- `storage_provider`
- `storage_path`
- `original_filename`
- `mime_type`
- `file_size`
- `checksum`
- `created_at`

说明：

- 不建议只靠本地文件名
- 将来迁移到 OSS、S3、MinIO 会更容易

---

## 4.17 document_chunks

作用：

- 保存切片业务信息

建议字段：

- `id`
- `document_id`
- `document_version_id`
- `chunk_index`
- `content`
- `token_count`
- `metadata_json`
- `qdrant_point_id`
- `embedding_model`
- `created_at`

说明：

- 业务上应能从数据库追踪切片
- 不建议完全依赖 Qdrant 保存切片信息

---

## 4.18 tag_definitions

作用：

- 管理标签定义

建议字段：

- `id`
- `scope_type`
- `scope_id`
- `name`
- `color`
- `description`
- `created_at`

说明：

- 可支持企业统一标签或部门内标签

---

## 4.19 document_tags

作用：

- 建立文档与标签关系

建议字段：

- `id`
- `document_id`
- `tag_id`

建议唯一约束：

- `(document_id, tag_id)`

---

## 4.20 document_shares

作用：

- 描述文档共享策略

建议字段：

- `id`
- `document_id`
- `share_type`
- `target_department_id`
- `target_role_code`
- `allow_search`
- `allow_view`
- `allow_download`
- `status`
- `created_by`
- `approved_by`
- `created_at`
- `updated_at`

建议共享类型：

- `department_only`
- `descendants`
- `specific_department`
- `org_public`
- `role_based`

说明：

- 不建议用一个 `is_shared`
- 共享应可审批、可撤回、可停用

---

## 4.21 knowledge_base_shares

作用：

- 描述知识库级共享策略

建议字段：

- `id`
- `knowledge_base_id`
- `share_type`
- `target_department_id`
- `target_role_code`
- `status`
- `created_by`
- `approved_by`
- `created_at`

说明：

- 有些场景是整个空间共享，而非单文档共享

---

## 4.22 approval_requests

作用：

- 表示审批主单

建议字段：

- `id`
- `request_type`
- `resource_type`
- `resource_id`
- `applicant_user_id`
- `current_step_no`
- `status`
- `submitted_at`
- `finished_at`
- `created_at`

建议 request_type：

- `department_join`
- `document_publish`
- `document_share`
- `role_upgrade`

---

## 4.23 approval_steps

作用：

- 定义审批步骤

建议字段：

- `id`
- `approval_request_id`
- `step_no`
- `reviewer_type`
- `reviewer_user_id`
- `reviewer_department_id`
- `status`
- `created_at`

说明：

- 将来可支持多级审批、会签、按角色审批

---

## 4.24 approval_records

作用：

- 记录审批动作

建议字段：

- `id`
- `approval_request_id`
- `step_id`
- `reviewer_user_id`
- `action`
- `comment`
- `acted_at`

说明：

- 用于保留审计轨迹

---

## 4.25 resource_access_policies

作用：

- 作为更通用的资源访问策略模型

建议字段：

- `id`
- `resource_type`
- `resource_id`
- `subject_type`
- `subject_id`
- `action`
- `effect`
- `conditions_json`
- `created_at`

说明：

- 如果未来权限模型进一步复杂，可统一升级到策略表
- MVP 阶段不一定必须落地，但数据库设计应预留思路

---

## 4.26 search_sessions

作用：

- 记录一轮问答或检索会话

建议字段：

- `id`
- `user_id`
- `knowledge_base_scope_json`
- `department_scope_json`
- `created_at`

说明：

- 有助于追踪问答上下文与统计

---

## 4.27 search_logs

作用：

- 记录一次实际检索行为

建议字段：

- `id`
- `session_id`
- `user_id`
- `query_text`
- `retrieval_mode`
- `result_count`
- `latency_ms`
- `created_at`

说明：

- 可支撑审计、效果分析和调优

---

## 4.28 document_access_logs

作用：

- 记录谁访问过哪些文档

建议字段：

- `id`
- `user_id`
- `document_id`
- `action`
- `access_context`
- `created_at`

说明：

- 企业场景常需要保留浏览、下载、引用等访问记录

---

## 4.29 audit_logs

作用：

- 记录关键治理动作

建议字段：

- `id`
- `actor_user_id`
- `action`
- `resource_type`
- `resource_id`
- `before_json`
- `after_json`
- `ip_address`
- `user_agent`
- `created_at`

说明：

- 对审批、角色变更、共享变更等动作非常重要

---

## 5. 关键状态与枚举建议

建议尽量统一枚举命名，避免不同表同义不同值。

### 5.1 通用状态

- `active`
- `inactive`
- `disabled`
- `archived`

### 5.2 申请/审批状态

- `pending`
- `approved`
- `rejected`
- `cancelled`

### 5.3 文档状态

- `draft`
- `pending_review`
- `published`
- `archived`
- `disabled`

### 5.4 可见性级别

- `private_to_department`
- `shared_to_descendants`
- `shared_to_specific_departments`
- `org_public`
- `restricted`

### 5.5 成员关系类型

- `primary`
- `secondary`
- `borrowed`
- `collaborative`

---

## 6. 与 Qdrant 的数据映射建议

Qdrant payload 建议至少包含：

- `document_id`
- `document_version_id`
- `knowledge_base_id`
- `department_id`
- `visibility_level`
- `status`
- `owner_user_id`
- `shared_department_ids`
- `chunk_index`

说明：

- 这些字段不是为了替代 PostgreSQL
- 而是为了让检索时能带过滤条件

推荐原则：

- PostgreSQL 保存完整事实
- Qdrant 保存检索需要的最小过滤字段

---

## 7. 建表优先级建议

## 第一优先级

先建这些表：

- `users`
- `departments`
- `department_memberships`
- `department_join_requests`
- `roles`
- `user_roles`
- `knowledge_bases`
- `documents`

原因：

- 先把组织和知识空间骨架立起来

## 第二优先级

- `document_versions`
- `document_files`
- `document_chunks`
- `document_shares`
- `approval_requests`
- `approval_records`

原因：

- 补齐文档治理与审批

## 第三优先级

- `permissions`
- `role_permissions`
- `knowledge_base_members`
- `knowledge_base_policies`
- `search_logs`
- `audit_logs`

原因：

- 进入企业治理增强阶段

---

## 8. MVP 最小表集合

如果要先做最小可用企业版，建议第一批只落这些：

- `users`
- `departments`
- `department_memberships`
- `department_join_requests`
- `roles`
- `user_roles`
- `knowledge_bases`
- `documents`
- `document_versions`
- `document_shares`
- `approval_requests`
- `approval_records`

这样已经可以支持：

- 注册登录
- 申请加入部门
- 部门负责人审批
- 建立知识库空间
- 上传文档
- 配置私有 / 共享
- 发布文档
- 权限内查看与检索

---

## 9. 当前项目迁移建议

当前项目已有：

- `users`
- 文档上传逻辑
- Qdrant 入库逻辑

建议迁移顺序：

### 第一步

扩展现有 `users`，但不要把组织字段直接写死为唯一归属。

### 第二步

新增：

- `departments`
- `department_memberships`
- `department_join_requests`

### 第三步

把“RAG 文档”从纯上传行为升级为“归属知识库空间的文档实体”：

- `knowledge_bases`
- `documents`
- `document_versions`

### 第四步

为 Qdrant payload 增加：

- `department_id`
- `knowledge_base_id`
- `document_id`
- `visibility_level`
- `status`

### 第五步

实现权限过滤检索，不再按全量集合裸查。

---

## 10. 索引与约束建议

推荐重点索引：

- `users.email`
- `users.username`
- `departments.parent_id`
- `departments.path`
- `department_memberships.user_id`
- `department_memberships.department_id`
- `knowledge_bases.department_id`
- `documents.knowledge_base_id`
- `documents.department_id`
- `documents.status`
- `documents.visibility_level`
- `document_versions.document_id`
- `document_chunks.document_id`
- `approval_requests.status`
- `approval_requests.request_type`
- `search_logs.user_id`

推荐唯一约束：

- `roles.code`
- `permissions.code`
- `departments.code`
- `knowledge_bases.code`
- `document_versions(document_id, version_no)`

---

## 11. 设计结论

最优数据库设计方向不是“继续在现有几张表上拼字段”，而是建立清晰的企业知识治理数据模型：

- 账号与身份分离
- 用户与组织分离
- 组织与知识空间分离
- 文档与版本分离
- 权限与共享策略分离
- 审批与审计独立建模

一句话总结：

`PostgreSQL 负责业务事实，Qdrant 负责权限范围内的向量召回。`

---

## 12. 下一步建议

建议下一份继续输出：

《企业级 RAG 前后端接口设计草案》

内容重点应包括：

- 注册、登录、加入部门、审批流 API
- 知识库空间管理 API
- 文档上传、共享、发布、下架 API
- 权限过滤检索 API
- 前端页面如何按这些 API 组织交互

只有数据库设计和接口设计接上，后续编码才会稳。
