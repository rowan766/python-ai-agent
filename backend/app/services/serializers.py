import json
from datetime import datetime
from typing import Any

from app.models import (
    Department,
    DictData,
    DictType,
    Document,
    DocumentChunk,
    DocumentTask,
    FileRecord,
    Menu,
    Role,
    User,
)


def format_datetime(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def serialize_department(department: Department) -> dict[str, Any]:
    return {
        "id": department.id,
        "name": department.name,
        "code": department.code,
        "parentId": department.parent_id,
        "leaderId": department.leader_id,
        "phone": department.phone,
        "email": department.email,
        "sort": department.sort,
        "status": department.status,
        "description": department.description,
        "createdAt": format_datetime(department.created_at),
        "updatedAt": format_datetime(department.updated_at),
    }


def serialize_menu(menu: Menu) -> dict[str, Any]:
    return {
        "id": menu.id,
        "parentId": menu.parent_id,
        "name": menu.name,
        "title": menu.title,
        "type": menu.type,
        "path": menu.path,
        "component": menu.component,
        "permission": menu.permission,
        "icon": menu.icon,
        "sort": menu.sort,
        "visible": menu.visible,
        "status": menu.status,
        "createdAt": format_datetime(menu.created_at),
        "updatedAt": format_datetime(menu.updated_at),
    }


def serialize_role(role: Role, *, include_relations: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "description": role.description,
        "dataScope": role.data_scope,
        "sort": role.sort,
        "status": role.status,
        "createdAt": format_datetime(role.created_at),
        "updatedAt": format_datetime(role.updated_at),
    }
    if include_relations:
        payload["menus"] = [
            {
                "roleId": relation.role_id,
                "menuId": relation.menu_id,
                "createdAt": format_datetime(relation.created_at),
                "menu": serialize_menu(relation.menu) if relation.menu else None,
            }
            for relation in sorted(role.role_menus, key=lambda item: item.menu_id)
        ]
        payload["departments"] = [
            {
                "roleId": relation.role_id,
                "departmentId": relation.department_id,
                "createdAt": format_datetime(relation.created_at),
                "department": serialize_department(relation.department) if relation.department else None,
            }
            for relation in sorted(role.role_departments, key=lambda item: item.department_id)
        ]
    return payload


def serialize_user(user: User, *, include_relations: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "avatarId": user.avatar_id,
        "avatarName": user.avatar_name,
        "departmentId": user.department_id,
        "gender": user.gender,
        "status": user.status,
        "createdAt": format_datetime(user.created_at),
        "updatedAt": format_datetime(user.updated_at),
        "lastLoginAt": format_datetime(user.last_login_at),
    }
    if include_relations:
        payload["department"] = serialize_department(user.department) if user.department else None
        payload["roles"] = [
            {
                "userId": relation.user_id,
                "roleId": relation.role_id,
                "createdAt": format_datetime(relation.created_at),
                "role": serialize_role(relation.role) if relation.role else None,
            }
            for relation in sorted(user.user_roles, key=lambda item: item.role_id)
        ]
    return payload


def serialize_dict_type(dict_type: DictType) -> dict[str, Any]:
    return {
        "id": dict_type.id,
        "name": dict_type.name,
        "code": dict_type.code,
        "description": dict_type.description,
        "sort": dict_type.sort,
        "status": dict_type.status,
        "createdAt": format_datetime(dict_type.created_at),
        "updatedAt": format_datetime(dict_type.updated_at),
    }


def serialize_dict_data(dict_data: DictData) -> dict[str, Any]:
    return {
        "id": dict_data.id,
        "dictTypeId": dict_data.dict_type_id,
        "label": dict_data.label,
        "value": dict_data.value,
        "sort": dict_data.sort,
        "cssClass": dict_data.css_class,
        "remark": dict_data.remark,
        "status": dict_data.status,
        "createdAt": format_datetime(dict_data.created_at),
        "updatedAt": format_datetime(dict_data.updated_at),
    }


def serialize_file_record(file_record: FileRecord) -> dict[str, Any]:
    return {
        "id": file_record.id,
        "userId": file_record.user_id,
        "name": file_record.original_name,
        "originalName": file_record.original_name,
        "storedName": file_record.file_name,
        "size": file_record.file_size,
        "mimeType": file_record.mime_type,
        "bucketName": file_record.bucket_name,
        "bucketType": file_record.bucket_type,
        "folder": file_record.folder,
        "url": file_record.file_url,
        "status": file_record.status,
        "createdAt": format_datetime(file_record.created_at),
        "updatedAt": format_datetime(file_record.updated_at),
    }


def serialize_document_task(task: DocumentTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "documentId": task.document_id,
        "taskType": task.task_type,
        "queueName": task.queue_name,
        "status": task.status,
        "attempts": task.attempts,
        "errorMessage": task.error_message,
        "startedAt": format_datetime(task.started_at),
        "finishedAt": format_datetime(task.finished_at),
        "createdAt": format_datetime(task.created_at),
        "updatedAt": format_datetime(task.updated_at),
    }


def serialize_document_chunk(chunk: DocumentChunk) -> dict[str, Any]:
    metadata = None
    if chunk.metadata_json:
        try:
            metadata = json.loads(chunk.metadata_json)
        except json.JSONDecodeError:
            metadata = {"raw": chunk.metadata_json}

    return {
        "id": chunk.id,
        "documentId": chunk.document_id,
        "taskId": chunk.task_id,
        "chunkIndex": chunk.chunk_index,
        "content": chunk.content,
        "contentLength": chunk.content_length,
        "charStart": chunk.char_start,
        "charEnd": chunk.char_end,
        "status": chunk.status,
        "metadata": metadata,
        "createdAt": format_datetime(chunk.created_at),
        "updatedAt": format_datetime(chunk.updated_at),
    }


def serialize_document(
    document: Document,
    *,
    include_file: bool = True,
    include_tasks: bool = False,
    include_chunks: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": document.id,
        "userId": document.user_id,
        "fileId": document.file_id,
        "title": document.title,
        "fileName": document.file_name,
        "mimeType": document.mime_type,
        "fileSize": document.file_size,
        "status": document.status,
        "parseMode": document.parse_mode,
        "textLength": document.text_length,
        "chunkCount": document.chunk_count,
        "errorMessage": document.error_message,
        "processedAt": format_datetime(document.processed_at),
        "createdAt": format_datetime(document.created_at),
        "updatedAt": format_datetime(document.updated_at),
    }
    if include_file:
        payload["file"] = serialize_file_record(document.file_record) if document.file_record else None
    if include_tasks:
        payload["tasks"] = [
            serialize_document_task(task)
            for task in sorted(document.tasks, key=lambda item: item.id, reverse=True)
        ]
    if include_chunks:
        payload["chunks"] = [
            serialize_document_chunk(chunk)
            for chunk in sorted(document.chunks, key=lambda item: item.chunk_index)
        ]
    return payload


def build_tree(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    item_map = {item["id"]: {**item, "children": []} for item in items}
    tree: list[dict[str, Any]] = []

    for item in item_map.values():
        parent_id = item.get("parentId")
        parent = item_map.get(parent_id)
        if parent:
            parent["children"].append(item)
        else:
            tree.append(item)

    def sort_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nodes.sort(key=lambda node: (node.get("sort", 0), node.get("id", 0)))
        for node in nodes:
            sort_nodes(node["children"])
        return nodes

    return sort_nodes(tree)
