from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Department(Base, TimestampMixin):
    __tablename__ = "sys_department"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    code: Mapped[str | None] = mapped_column(String(50), unique=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("sys_department.id", ondelete="SET NULL"))
    leader_id: Mapped[int | None] = mapped_column(Integer)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    sort: Mapped[int] = mapped_column(default=0)
    status: Mapped[int] = mapped_column(default=1)
    description: Mapped[str | None] = mapped_column(String(200))

    users: Mapped[list["User"]] = relationship(back_populates="department")
    role_departments: Mapped[list["RoleDepartment"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
    )


class Role(Base, TimestampMixin):
    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(200))
    data_scope: Mapped[int] = mapped_column(default=1)
    sort: Mapped[int] = mapped_column(default=0)
    status: Mapped[int] = mapped_column(default=1)

    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="role", cascade="all, delete-orphan")
    role_menus: Mapped[list["RoleMenu"]] = relationship(back_populates="role", cascade="all, delete-orphan")
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )
    role_departments: Mapped[list["RoleDepartment"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )


class Menu(Base, TimestampMixin):
    __tablename__ = "sys_menu"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("sys_menu.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(20))
    path: Mapped[str | None] = mapped_column(String(200))
    component: Mapped[str | None] = mapped_column(String(200))
    permission: Mapped[str | None] = mapped_column(String(100))
    icon: Mapped[str | None] = mapped_column(String(50))
    sort: Mapped[int] = mapped_column(default=0)
    visible: Mapped[int] = mapped_column(default=1)
    status: Mapped[int] = mapped_column(default=1)

    role_menus: Mapped[list["RoleMenu"]] = relationship(back_populates="menu", cascade="all, delete-orphan")


class Permission(Base, TimestampMixin):
    __tablename__ = "sys_permission"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    path: Mapped[str | None] = mapped_column(String(200))
    method: Mapped[str | None] = mapped_column(String(10))
    description: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[int] = mapped_column(default=1)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class User(Base, TimestampMixin):
    __tablename__ = "sys_user"
    __table_args__ = (
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
        Index("idx_user_department_id", "department_id"),
        Index("idx_user_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(100), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    avatar: Mapped[str | None] = mapped_column(String(255))
    avatar_id: Mapped[int | None] = mapped_column(Integer)
    avatar_name: Mapped[str | None] = mapped_column(String(255))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("sys_department.id", ondelete="SET NULL"))
    gender: Mapped[int] = mapped_column(default=0)
    status: Mapped[int] = mapped_column(default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    department: Mapped[Department | None] = relationship(back_populates="users")
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    files: Mapped[list["FileRecord"]] = relationship(back_populates="user")
    documents: Mapped[list["Document"]] = relationship(back_populates="user")
    document_qa_sessions: Mapped[list["DocumentQaSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserRole(Base):
    __tablename__ = "sys_user_role"

    user_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        default=datetime.utcnow,
    )

    user: Mapped[User] = relationship(back_populates="user_roles")
    role: Mapped[Role] = relationship(back_populates="user_roles")


class RoleMenu(Base):
    __tablename__ = "sys_role_menu"

    role_id: Mapped[int] = mapped_column(ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("sys_menu.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        default=datetime.utcnow,
    )

    role: Mapped[Role] = relationship(back_populates="role_menus")
    menu: Mapped[Menu] = relationship(back_populates="role_menus")


class RolePermission(Base):
    __tablename__ = "sys_role_permission"

    role_id: Mapped[int] = mapped_column(ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("sys_permission.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        default=datetime.utcnow,
    )

    role: Mapped[Role] = relationship(back_populates="role_permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_permissions")


class RoleDepartment(Base):
    __tablename__ = "sys_role_department"

    role_id: Mapped[int] = mapped_column(ForeignKey("sys_role.id", ondelete="CASCADE"), primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("sys_department.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        default=datetime.utcnow,
    )

    role: Mapped[Role] = relationship(back_populates="role_departments")
    department: Mapped[Department] = relationship(back_populates="role_departments")


class FileRecord(Base, TimestampMixin):
    __tablename__ = "sys_file"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id", ondelete="CASCADE"))
    bucket_name: Mapped[str] = mapped_column(String(100))
    bucket_type: Mapped[str] = mapped_column(String(50))
    folder: Mapped[str] = mapped_column(String(100))
    file_name: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    file_url: Mapped[str] = mapped_column(Text)
    status: Mapped[int] = mapped_column(default=1)

    user: Mapped[User] = relationship(back_populates="files")
    document: Mapped["Document | None"] = relationship(back_populates="file_record")


class DictType(Base, TimestampMixin):
    __tablename__ = "sys_dict_type"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(200))
    sort: Mapped[int] = mapped_column(default=0)
    status: Mapped[int] = mapped_column(default=1)

    items: Mapped[list["DictData"]] = relationship(back_populates="dict_type", cascade="all, delete-orphan")


class DictData(Base, TimestampMixin):
    __tablename__ = "sys_dict_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dict_type_id: Mapped[int] = mapped_column(ForeignKey("sys_dict_type.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(String(50))
    sort: Mapped[int] = mapped_column(default=0)
    css_class: Mapped[str | None] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[int] = mapped_column(default=1)

    dict_type: Mapped[DictType] = relationship(back_populates="items")


class Document(Base, TimestampMixin):
    __tablename__ = "sys_document"
    __table_args__ = (
        Index("idx_document_user_id", "user_id"),
        Index("idx_document_status", "status"),
        Index("idx_document_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id", ondelete="CASCADE"))
    file_id: Mapped[int] = mapped_column(ForeignKey("sys_file.id", ondelete="CASCADE"), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    parse_mode: Mapped[str] = mapped_column(String(20), default="auto")
    text_length: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="documents")
    file_record: Mapped[FileRecord] = relationship(back_populates="document")
    tasks: Mapped[list["DocumentTask"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentTask(Base, TimestampMixin):
    __tablename__ = "sys_document_task"
    __table_args__ = (
        Index("idx_document_task_document_id", "document_id"),
        Index("idx_document_task_status", "status"),
        Index("idx_document_task_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("sys_document.id", ondelete="CASCADE"))
    task_type: Mapped[str] = mapped_column(String(50), default="ingest")
    queue_name: Mapped[str] = mapped_column(String(50), default="document-processing")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="tasks")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="task")


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "sys_document_chunk"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("sys_document.id", ondelete="CASCADE"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("sys_document_task.id", ondelete="SET NULL"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_length: Mapped[int] = mapped_column(Integer)
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="ready")
    metadata_json: Mapped[str | None] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="chunks")
    task: Mapped[DocumentTask | None] = relationship(back_populates="chunks")


class DocumentQaSession(Base, TimestampMixin):
    __tablename__ = "sys_document_qa_session"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_user.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(255))
    document_ids_json: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="document_qa_sessions")
    messages: Mapped[list["DocumentQaMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DocumentQaMessage.id.asc()",
    )


class DocumentQaMessage(Base, TimestampMixin):
    __tablename__ = "sys_document_qa_message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sys_document_qa_session.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    answer_mode: Mapped[str | None] = mapped_column(String(50))
    answer_model: Mapped[str | None] = mapped_column(String(100))
    sources_json: Mapped[str | None] = mapped_column(Text)
    suggestions_json: Mapped[str | None] = mapped_column(Text)
    message_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session: Mapped[DocumentQaSession] = relationship(back_populates="messages")
