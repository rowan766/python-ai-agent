from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Department,
    DictData,
    DictType,
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
    {"id": 1, "name": "省养护处", "code": "root", "parent_id": None, "leader_id": 1, "phone": "027-00000000", "email": "root@example.com", "sort": 0, "status": 1, "description": "省养护处"},
    {"id": 3, "name": "襄阳市", "code": "420000000000", "parent_id": 1, "leader_id": 3, "phone": "027-66666666", "email": "rd@example.com", "sort": 1, "status": 1, "description": "襄阳市"},
    {"id": 4, "name": "武汉市", "code": "420100000000", "parent_id": 1, "leader_id": 4, "phone": "027-66666666", "email": "rd@example.com", "sort": 2, "status": 1, "description": "武汉市养护中心"},
    {"id": 5, "name": "襄城区", "code": "420602000000", "parent_id": 3, "leader_id": 5, "phone": "15736542019", "email": "123@qq.com", "sort": 1, "status": 1, "description": "襄阳市-樊城区"},
    {"id": 6, "name": "南漳县", "code": "420624000000", "parent_id": 3, "leader_id": None, "phone": "15678921345", "email": "12345@qq.com", "sort": 2, "status": 1, "description": "襄阳市-南漳县"},
    {"id": 7, "name": "欧庙镇", "code": "omz", "parent_id": 5, "leader_id": None, "phone": None, "email": None, "sort": 1, "status": 1, "description": "襄阳-襄城-欧庙"},
]


ROLES = [
    {"id": 1, "name": "省管理员", "code": "admin", "description": "省管理员角色", "data_scope": 1, "sort": 0, "status": 1},
    {"id": 4, "name": "省", "code": "pyhzx", "description": "省", "data_scope": 2, "sort": 1, "status": 1},
    {"id": 5, "name": "市", "code": "syhzx", "description": "市", "data_scope": 2, "sort": 2, "status": 1},
    {"id": 6, "name": "县区", "code": "xyhzx", "description": "县区", "data_scope": 2, "sort": 3, "status": 1},
    {"id": 7, "name": "站", "code": "yhz", "description": "站", "data_scope": 2, "sort": 4, "status": 1},
    {"id": 8, "name": "人员", "code": "yhy", "description": "人员", "data_scope": 4, "sort": 5, "status": 1},
]


MENUS = [
    {"id": 3, "parent_id": None, "name": "Dashboard", "title": "首页", "type": "menu", "path": "/dashboard", "component": "views/Dashboard", "permission": None, "icon": "HomeFilled", "sort": 1, "visible": 1, "status": 1},
    {"id": 4, "parent_id": None, "name": "System", "title": "系统管理", "type": "menu", "path": "/system", "component": None, "permission": None, "icon": "Setting", "sort": 10, "visible": 1, "status": 1},
    {"id": 5, "parent_id": 4, "name": "SystemUser", "title": "用户管理", "type": "menu", "path": "/system/user", "component": "views/system/User", "permission": None, "icon": "User", "sort": 11, "visible": 1, "status": 1},
    {"id": 6, "parent_id": 4, "name": "SystemRole", "title": "角色管理", "type": "menu", "path": "/system/role", "component": "views/system/Role", "permission": None, "icon": "Avatar", "sort": 12, "visible": 1, "status": 1},
    {"id": 7, "parent_id": 4, "name": "SystemMenu", "title": "菜单管理", "type": "menu", "path": "/system/menu", "component": "views/system/Menu", "permission": None, "icon": "Menu", "sort": 13, "visible": 1, "status": 1},
    {"id": 8, "parent_id": 4, "name": "SystemDict", "title": "数据字典", "type": "menu", "path": "/system/dict", "component": "views/system/Dict", "permission": None, "icon": "Document", "sort": 14, "visible": 1, "status": 1},
    {"id": 9, "parent_id": 4, "name": "SystemDepartment", "title": "部门管理", "type": "menu", "path": "/system/department", "component": "views/system/Department", "permission": None, "icon": "OfficeBuilding", "sort": 15, "visible": 1, "status": 1},
    {"id": 10, "parent_id": None, "name": "AssetManagement", "title": "资源管理", "type": "menu", "path": "/asset", "component": None, "permission": None, "icon": "Menu", "sort": 3, "visible": 1, "status": 1},
    {"id": 11, "parent_id": 10, "name": "AssetBridge", "title": "桥梁管理", "type": "menu", "path": "/asset/bridge", "component": "views/assetManagement/Bridge", "permission": None, "icon": None, "sort": 1, "visible": 1, "status": 1},
    {"id": 12, "parent_id": 10, "name": "AssetTunnel", "title": "隧道管理", "type": "menu", "path": "/asset/tunnel", "component": "views/assetManagement/Tunnel", "permission": None, "icon": None, "sort": 2, "visible": 1, "status": 1},
    {"id": 13, "parent_id": 10, "name": "AssetFacility", "title": "附属设施", "type": "menu", "path": "/asset/facility", "component": "views/assetManagement/Facility", "permission": None, "icon": None, "sort": 3, "visible": 1, "status": 1},
    {"id": 14, "parent_id": 10, "name": "AssetStation", "title": "养护站管理", "type": "menu", "path": "/asset/station", "component": "views/assetManagement/Station", "permission": None, "icon": None, "sort": 4, "visible": 1, "status": 1},
    {"id": 15, "parent_id": 11, "name": "asset:bridge:create", "title": "新增", "type": "button", "path": None, "component": None, "permission": "asset:bridge:create", "icon": None, "sort": 1, "visible": 1, "status": 1},
    {"id": 16, "parent_id": 11, "name": "asset:bridge:update", "title": "编辑", "type": "button", "path": None, "component": None, "permission": "asset:bridge:update", "icon": None, "sort": 2, "visible": 1, "status": 1},
    {"id": 17, "parent_id": 11, "name": "asset:bridge:delete", "title": "删除", "type": "button", "path": None, "component": None, "permission": "asset:bridge:delete", "icon": None, "sort": 3, "visible": 1, "status": 1},
]


ROLE_MENUS = [
    (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (1, 11), (1, 12), (1, 13), (1, 14), (1, 15), (1, 16), (1, 17),
    (4, 3), (4, 10), (4, 11), (4, 12), (4, 13), (4, 14),
    (5, 3), (5, 10), (5, 11), (5, 12), (5, 13), (5, 14),
    (6, 3), (6, 10), (6, 11), (6, 12), (6, 13), (6, 14),
    (7, 3), (7, 10), (7, 11), (7, 12), (7, 13), (7, 14),
    (8, 3), (8, 10), (8, 11), (8, 12), (8, 13), (8, 14),
]


USERS = [
    {"id": 1, "username": "admin", "nickname": "管理员", "email": "admin@example.com", "phone": None, "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 1, "gender": 1, "status": 1},
    {"id": 3, "username": "zhangsan", "nickname": "张三", "email": "row287630@gmail.com", "phone": None, "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 3, "gender": 1, "status": 1},
    {"id": 4, "username": "lisi", "nickname": "李四", "email": "123@qq.com", "phone": None, "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 4, "gender": 2, "status": 1},
    {"id": 5, "username": "wangwu", "nickname": "王五", "email": "1234@qq.com", "phone": None, "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 5, "gender": 1, "status": 1},
    {"id": 6, "username": "zhaoliu", "nickname": "赵六", "email": "12345@qq.com", "phone": None, "avatar": None, "avatar_id": None, "avatar_name": None, "department_id": 6, "gender": 1, "status": 1},
]


USER_ROLES = [
    (1, 1),
    (3, 5),
    (4, 5),
    (5, 6),
    (6, 6),
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


def seed_database(db: Session) -> None:
    existing_user = db.scalar(select(User.id).limit(1))
    if existing_user:
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
    _sync_postgres_sequences(db)
    db.commit()
