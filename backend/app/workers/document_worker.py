import time

from app.services.document_processor import process_document_task
from app.services.document_queue import pop_document_task


def main() -> None:
    print("文档处理 Worker 已启动，正在监听队列...")
    while True:
        task_id = pop_document_task(block=True, timeout=5)
        if task_id is None:
            continue
        try:
            process_document_task(task_id)
        except Exception as exc:
            print(f"文档任务处理失败: task_id={task_id}, error={exc}")
            time.sleep(1)


if __name__ == "__main__":
    main()
