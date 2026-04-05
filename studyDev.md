## 开发执行命令级说明

### uv run uvicorn app.main:app --reload --port 8000
    
    uv run：在项目的虚拟环境里运行命令（等价于 npm run）
    uvicorn app.main:app：启动 app/main.py 里的 app 对象
    --reload：代码改动后自动重启，等价于 nodemon
    --port 8000：监听 8000 端口

### 启动代码
    uv run uvicorn app.main:app --reload --port 8000

## RAG 上传与向量入库说明

### 上传文件会去哪里
    上传接口是 /api/rag/upload
    代码位置：app/api/rag.py
    文件会先被临时保存到项目根目录下的 uploads/ 目录
    保存方式：UPLOAD_DIR / file.filename

### 上传后为什么本地看不到文件
    上传完成后，系统会立即解析文件内容
    然后进入 finally 逻辑，把 uploads/ 里的临时文件删除
    删除代码在 app/api/rag.py 里的 file_path.unlink()
    所以原始 PDF/Word/TXT 文件不会长期保留在项目目录中

### 真正长期保存的是什么
    真正保留下来的是“切片后的文本 + 向量”，不是原文件本身
    这些数据会被写入 Qdrant
    当前集合名：knowledge_base
    代码位置：app/core/rag/indexer.py

### 文件进入 Qdrant 之前做了什么
    代码位置：app/core/rag/loader.py
    系统会先根据文件扩展名选择对应 loader
    例如 PDF 使用 PyPDFLoader
    读出文本后，再用 RecursiveCharacterTextSplitter 切分
    当前切片参数：
        chunk_size = 500
        chunk_overlap = 50

### Qdrant 里存的是什么
    代码位置：app/core/rag/indexer.py
    每个切片都会生成一个 PointStruct
    里面主要有三部分：
        id：随机生成的唯一 ID
        vector：embedding 向量
        payload：附加数据

### payload 里保存了什么
    payload.page_content：切片后的文本内容
    payload.metadata：页码、来源等元信息

### 检索时发生了什么
    代码位置：app/core/rag/retriever.py
    用户 query 会先生成 embedding 向量
    然后去 Qdrant 的 knowledge_base 集合做相似度检索
    如果向量检索没有命中，或者 embedding 服务临时不可用
    当前项目还会自动降级到关键词匹配，避免直接返回空结果

### 当前项目里的实际情况
    你测试上传的 PDF 已经成功写进 Qdrant
    我本地检查到 knowledge_base 里已有 4 个 points
    这说明文件已经被成功切片并入库
