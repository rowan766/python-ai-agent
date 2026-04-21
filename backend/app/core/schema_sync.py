from sqlalchemy import inspect, text

from app.core.database import engine


def ensure_runtime_schema() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("sys_document"):
            return

        existing_columns = {column["name"] for column in inspector.get_columns("sys_document")}
        missing_column_sql: list[str] = []
        if "space_id" not in existing_columns:
            missing_column_sql.append("ALTER TABLE sys_document ADD COLUMN space_id INTEGER")
        if "owner_user_id" not in existing_columns:
            missing_column_sql.append("ALTER TABLE sys_document ADD COLUMN owner_user_id INTEGER")
        if "owner_department_id" not in existing_columns:
            missing_column_sql.append("ALTER TABLE sys_document ADD COLUMN owner_department_id INTEGER")
        if inspector.has_table("sys_document_qa_session"):
            session_columns = {column["name"] for column in inspector.get_columns("sys_document_qa_session")}
            if "space_id" not in session_columns:
                connection.execute(text("ALTER TABLE sys_document_qa_session ADD COLUMN space_id INTEGER"))

        for statement in missing_column_sql:
            connection.execute(text(statement))

        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_document_space_id ON sys_document (space_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_document_owner_user_id ON sys_document (owner_user_id)"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS idx_document_owner_department_id ON sys_document (owner_department_id)")
        )

        if connection.dialect.name == "postgresql":
            connection.execute(
                text(
                    """
                    UPDATE sys_document AS d
                    SET
                        owner_user_id = COALESCE(d.owner_user_id, d.user_id),
                        owner_department_id = COALESCE(d.owner_department_id, u.department_id)
                    FROM sys_user AS u
                    WHERE d.user_id = u.id
                    """
                )
            )
        else:
            connection.execute(
                text(
                    """
                    UPDATE sys_document
                    SET
                        owner_user_id = COALESCE(owner_user_id, user_id),
                        owner_department_id = COALESCE(
                            owner_department_id,
                            (SELECT department_id FROM sys_user WHERE sys_user.id = sys_document.user_id)
                        )
                    """
                )
            )
