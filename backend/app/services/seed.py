from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Department,
    DictData,
    DictType,
    Document,
    DocumentChunk,
    DocumentTask,
    FileRecord,
    Menu,
    Permission,
    Role,
    RoleMenu,
    User,
    UserRole,
)


DEFAULT_PASSWORD = "123456"


DEPARTMENTS = [
    {"id": 1, "name": "集团总部", "code": "root", "parent_id": None, "leader_id": 1, "phone": "010-88888888", "email": "admin@company.com", "sort": 0, "status": 1, "description": "集团总部"},
    {"id": 2, "name": "技术研发部", "code": "tech", "parent_id": 1, "leader_id": 3, "phone": "010-88888801", "email": "tech@company.com", "sort": 1, "status": 1, "description": "负责平台技术研发与AI能力建设"},
    {"id": 3, "name": "产品运营部", "code": "product", "parent_id": 1, "leader_id": 4, "phone": "010-88888802", "email": "product@company.com", "sort": 2, "status": 1, "description": "负责产品设计与知识库运营"},
    {"id": 4, "name": "市场销售部", "code": "sales", "parent_id": 1, "leader_id": None, "phone": "010-88888803", "email": "sales@company.com", "sort": 3, "status": 1, "description": "负责市场推广与客户关系管理"},
    {"id": 5, "name": "综合管理部", "code": "admin_dept", "parent_id": 1, "leader_id": 5, "phone": "010-88888804", "email": "hr@company.com", "sort": 4, "status": 1, "description": "负责行政、人事与综合事务"},
    {"id": 6, "name": "前端开发组", "code": "frontend", "parent_id": 2, "leader_id": None, "phone": None, "email": None, "sort": 1, "status": 1, "description": "技术研发部-前端开发"},
    {"id": 7, "name": "后端开发组", "code": "backend", "parent_id": 2, "leader_id": None, "phone": None, "email": None, "sort": 2, "status": 1, "description": "技术研发部-后端开发"},
]


ROLES = [
    {"id": 1, "name": "超级管理员", "code": "admin", "description": "系统最高权限，可访问所有数据与功能", "data_scope": 1, "sort": 0, "status": 1},
    {"id": 4, "name": "系统管理员", "code": "sys_admin", "description": "负责系统配置与用户权限管理，可查看全部门数据", "data_scope": 2, "sort": 1, "status": 1},
    {"id": 5, "name": "知识库管理员", "code": "kb_admin", "description": "负责知识空间与文档的维护管理", "data_scope": 2, "sort": 2, "status": 1},
    {"id": 6, "name": "部门主管", "code": "dept_manager", "description": "可查看并管理本部门范围内的知识资源", "data_scope": 3, "sort": 3, "status": 1},
    {"id": 7, "name": "普通用户", "code": "staff", "description": "日常使用知识库检索与AI问答功能", "data_scope": 4, "sort": 4, "status": 1},
    {"id": 8, "name": "访客", "code": "guest", "description": "只读访客，仅可使用AI助手进行问答", "data_scope": 4, "sort": 5, "status": 1},
]


MENUS = [
    # 顶级菜单
    {"id": 19, "parent_id": None, "name": "AiAssistant", "title": "AI 助手", "type": "menu", "path": "/ai-assistant", "component": "views/assetManagement/DocumentQa", "permission": None, "icon": "ChatDotRound", "sort": 0, "visible": 1, "status": 1},
    {"id": 3,  "parent_id": None, "name": "Dashboard", "title": "首页", "type": "menu", "path": "/dashboard", "component": "views/Dashboard", "permission": None, "icon": "HomeFilled", "sort": 1, "visible": 0, "status": 0},
    {"id": 10, "parent_id": None, "name": "AssetManagement", "title": "资源管理", "type": "menu", "path": "/asset", "component": None, "permission": None, "icon": "Files", "sort": 3, "visible": 1, "status": 1},
    {"id": 4,  "parent_id": None, "name": "System", "title": "系统管理", "type": "menu", "path": "/system", "component": None, "permission": None, "icon": "Setting", "sort": 10, "visible": 1, "status": 1},
    # 系统管理子菜单
    {"id": 5,  "parent_id": 4, "name": "SystemUser", "title": "用户管理", "type": "menu", "path": "/system/user", "component": "views/system/User", "permission": None, "icon": "User", "sort": 11, "visible": 1, "status": 1},
    {"id": 6,  "parent_id": 4, "name": "SystemRole", "title": "角色管理", "type": "menu", "path": "/system/role", "component": "views/system/Role", "permission": None, "icon": "Avatar", "sort": 12, "visible": 1, "status": 1},
    {"id": 7,  "parent_id": 4, "name": "SystemMenu", "title": "菜单管理", "type": "menu", "path": "/system/menu", "component": "views/system/Menu", "permission": None, "icon": "Menu", "sort": 13, "visible": 1, "status": 1},
    {"id": 8,  "parent_id": 4, "name": "SystemDict", "title": "数据字典", "type": "menu", "path": "/system/dict", "component": "views/system/Dict", "permission": None, "icon": "Document", "sort": 14, "visible": 1, "status": 1},
    {"id": 9,  "parent_id": 4, "name": "SystemDepartment", "title": "部门管理", "type": "menu", "path": "/system/department", "component": "views/system/Department", "permission": None, "icon": "OfficeBuilding", "sort": 15, "visible": 1, "status": 1},
    # 资源管理子菜单（已移除桥梁/隧道/附属设施/养护站）
    {"id": 27, "parent_id": 10, "name": "AssetKnowledgeSpace", "title": "知识空间", "type": "menu", "path": "/asset/knowledge-space", "component": "views/assetManagement/KnowledgeSpace", "permission": None, "icon": None, "sort": 1, "visible": 1, "status": 1},
    {"id": 18, "parent_id": 10, "name": "AssetDocument", "title": "文档处理", "type": "menu", "path": "/asset/document", "component": "views/assetManagement/Document", "permission": None, "icon": None, "sort": 2, "visible": 1, "status": 1},
    {"id": 20, "parent_id": 10, "name": "UploadTest", "title": "上传测试", "type": "menu", "path": "/asset/upload-test", "component": "views/Dashboard", "permission": None, "icon": None, "sort": 3, "visible": 1, "status": 1},
    # 上传测试-快捷操作按钮（原桥梁管理按钮迁移至此）
    {"id": 15, "parent_id": 20, "name": "upload:quick:create", "title": "快捷新增", "type": "button", "path": None, "component": None, "permission": "upload:quick:create", "icon": None, "sort": 1, "visible": 1, "status": 1},
    {"id": 16, "parent_id": 20, "name": "upload:quick:update", "title": "快捷编辑", "type": "button", "path": None, "component": None, "permission": "upload:quick:update", "icon": None, "sort": 2, "visible": 1, "status": 1},
    {"id": 17, "parent_id": 20, "name": "upload:quick:delete", "title": "快捷删除", "type": "button", "path": None, "component": None, "permission": "upload:quick:delete", "icon": None, "sort": 3, "visible": 1, "status": 1},
    # 文档处理按钮权限
    {"id": 21, "parent_id": 18, "name": "knowledge:space:create", "title": "创建空间", "type": "button", "path": None, "component": None, "permission": "knowledge:space:create", "icon": None, "sort": 1, "visible": 1, "status": 1},
    {"id": 22, "parent_id": 18, "name": "knowledge:space:share", "title": "共享空间", "type": "button", "path": None, "component": None, "permission": "knowledge:space:share", "icon": None, "sort": 2, "visible": 1, "status": 1},
    {"id": 23, "parent_id": 18, "name": "knowledge:document:upload", "title": "上传文档", "type": "button", "path": None, "component": None, "permission": "knowledge:document:upload", "icon": None, "sort": 3, "visible": 1, "status": 1},
    {"id": 24, "parent_id": 18, "name": "knowledge:document:download", "title": "下载文档", "type": "button", "path": None, "component": None, "permission": "knowledge:document:download", "icon": None, "sort": 4, "visible": 1, "status": 1},
    {"id": 25, "parent_id": 18, "name": "knowledge:document:reprocess", "title": "重试文档", "type": "button", "path": None, "component": None, "permission": "knowledge:document:reprocess", "icon": None, "sort": 5, "visible": 1, "status": 1},
    {"id": 26, "parent_id": 18, "name": "knowledge:document:delete", "title": "删除文档", "type": "button", "path": None, "component": None, "permission": "knowledge:document:delete", "icon": None, "sort": 6, "visible": 1, "status": 1},
]


ROLE_MENUS = [
    # 超级管理员(1)：全部菜单与按钮
    (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9),
    (1, 10), (1, 18), (1, 19), (1, 20), (1, 27),
    (1, 15), (1, 16), (1, 17),
    (1, 21), (1, 22), (1, 23), (1, 24), (1, 25), (1, 26),
    # 系统管理员(4)：系统管理全部 + 知识管理全部
    (4, 3), (4, 4), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9),
    (4, 10), (4, 18), (4, 19), (4, 20), (4, 27),
    (4, 21), (4, 22), (4, 23), (4, 24), (4, 25), (4, 26),
    # 知识库管理员(5)：知识管理全部 + 上传测试快捷操作，无系统管理
    (5, 3), (5, 10), (5, 18), (5, 19), (5, 20), (5, 27),
    (5, 15), (5, 16), (5, 17),
    (5, 21), (5, 22), (5, 23), (5, 24), (5, 25), (5, 26),
    # 部门主管(6)：可管理知识空间与文档，有上传/下载/重试/删除权限
    (6, 3), (6, 10), (6, 18), (6, 19), (6, 27),
    (6, 21), (6, 22), (6, 23), (6, 24), (6, 25), (6, 26),
    # 普通用户(7)：使用AI助手、上传/下载文档，可创建知识空间
    (7, 3), (7, 10), (7, 18), (7, 19), (7, 27),
    (7, 21), (7, 23), (7, 24), (7, 26),
    # 访客(8)：仅可使用AI助手进行问答
    (8, 19),
]


USERS = [
    {"id": 1, "username": "admin",    "nickname": "系统管理员", "email": "admin@company.com",   "phone": "13800000001", "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 1, "gender": 1, "status": 1},
    {"id": 3, "username": "zhangsan", "nickname": "张三",       "email": "zhangsan@company.com", "phone": "13800000003", "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 2, "gender": 1, "status": 1},
    {"id": 4, "username": "lisi",     "nickname": "李四",       "email": "lisi@company.com",     "phone": "13800000004", "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 3, "gender": 2, "status": 1},
    {"id": 5, "username": "wangwu",   "nickname": "王五",       "email": "wangwu@company.com",   "phone": "13800000005", "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 5, "gender": 1, "status": 1},
    {"id": 6, "username": "zhaoliu",  "nickname": "赵六",       "email": "zhaoliu@company.com",  "phone": "13800000006", "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 4, "gender": 1, "status": 1},
]


USER_ROLES = [
    (1, 1),  # admin       → 超级管理员
    (3, 4),  # zhangsan    → 系统管理员（技术研发部）
    (4, 5),  # lisi        → 知识库管理员（产品运营部）
    (5, 6),  # wangwu      → 部门主管（综合管理部）
    (6, 7),  # zhaoliu     → 普通用户（市场销售部）
]


DICT_TYPES = [
    {"id": 1, "name": "用户性别", "code": "user_gender", "description": "用户性别字典", "sort": 1, "status": 1},
]


DICT_DATA = [
    {"id": 1, "dict_type_id": 1, "label": "男", "value": "1", "sort": 1, "css_class": "primary", "remark": "男性用户", "status": 1},
    {"id": 2, "dict_type_id": 1, "label": "女", "value": "2", "sort": 2, "css_class": "primary", "remark": "女性用户", "status": 1},
]


def _sync_postgres_sequences(db: Session) -> None:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return

    sequence_targets = [
        Department.__tablename__,
        DictType.__tablename__,
        DictData.__tablename__,
        Document.__tablename__,
        DocumentTask.__tablename__,
        DocumentChunk.__tablename__,
        FileRecord.__tablename__,
        Menu.__tablename__,
        Permission.__tablename__,
        Role.__tablename__,
        User.__tablename__,
    ]

    for table_name in sequence_targets:
        db.execute(
            text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                    (SELECT COUNT(*) > 0 FROM {table_name})
                )
                """
            )
        )


# 已废弃的菜单 ID（桥梁/隧道/附属设施/养护站），增量同步时将其下线（status=0、visible=0）
_DEPRECATED_MENU_IDS = {11, 12, 13, 14}

# 当前有效菜单 ID 集合，增量同步时会清理不在此列的 role_menu 关联
_ACTIVE_MENU_IDS = {m["id"] for m in MENUS}


def _seed_incremental_menus(db: Session) -> bool:
    changed = False

    # Upsert 菜单
    existing_menu_ids = set(db.scalars(select(Menu.id)).all())
    for menu in MENUS:
        if menu["id"] in existing_menu_ids:
            existing = db.get(Menu, menu["id"])
            if existing:
                for key, value in menu.items():
                    setattr(existing, key, value)
                changed = True
        else:
            db.add(Menu(**menu))
            changed = True

    # 下线已废弃菜单（不删除，保留历史，但隐藏并禁用）
    for deprecated_id in _DEPRECATED_MENU_IDS:
        deprecated = db.get(Menu, deprecated_id)
        if deprecated and (deprecated.status != 0 or deprecated.visible != 0):
            deprecated.status = 0
            deprecated.visible = 0
            changed = True

    db.commit()

    # 清理废弃菜单的 role_menu 关联
    db.execute(delete(RoleMenu).where(RoleMenu.menu_id.in_(_DEPRECATED_MENU_IDS)))

    # 同步 role_menu：以 ROLE_MENUS 为准，先清掉活跃菜单的旧关联再重建
    db.execute(delete(RoleMenu).where(RoleMenu.menu_id.in_(_ACTIVE_MENU_IDS)))
    for role_id, menu_id in ROLE_MENUS:
        db.add(RoleMenu(role_id=role_id, menu_id=menu_id))
    changed = True

    # Upsert 角色
    existing_role_ids = set(db.scalars(select(Role.id)).all())
    for role in ROLES:
        if role["id"] in existing_role_ids:
            existing_role = db.get(Role, role["id"])
            if existing_role:
                for key, value in role.items():
                    setattr(existing_role, key, value)
        else:
            db.add(Role(**role))
        changed = True

    # Upsert 部门：先插入新部门并 flush，再更新已有部门
    # 必须分两步，否则更新已有部门时引用的新 parent_id 尚未入库会触发外键违反
    existing_dept_ids = set(db.scalars(select(Department.id)).all())
    for dept in DEPARTMENTS:
        if dept["id"] not in existing_dept_ids:
            db.add(Department(**{k: v for k, v in dept.items() if k != "parent_id"}, parent_id=None))
    db.flush()
    for dept in DEPARTMENTS:
        existing_dept = db.get(Department, dept["id"])
        if existing_dept:
            for key, value in dept.items():
                setattr(existing_dept, key, value)
    changed = True

    return changed


def seed_database(db: Session) -> None:
    existing_user = db.scalar(select(User.id).limit(1))
    if existing_user:
        if _seed_incremental_menus(db):
            db.commit()
            _sync_postgres_sequences(db)
            db.commit()
        return

    for department in DEPARTMENTS:
        db.add(Department(**department))

    for role in ROLES:
        db.add(Role(**role))

    for menu in MENUS:
        db.add(Menu(**menu))

    for dict_type in DICT_TYPES:
        db.add(DictType(**dict_type))

    for dict_data in DICT_DATA:
        db.add(DictData(**dict_data))

    hashed_password = hash_password(DEFAULT_PASSWORD)
    for user in USERS:
        db.add(User(**user, password=hashed_password))

    for user_id, role_id in USER_ROLES:
        db.add(UserRole(user_id=user_id, role_id=role_id))

    for role_id, menu_id in ROLE_MENUS:
        db.add(RoleMenu(role_id=role_id, menu_id=menu_id))

    db.commit()
    _seed_incremental_menus(db)
    _sync_postgres_sequences(db)
    db.commit()
