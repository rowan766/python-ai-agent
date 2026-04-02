## 开发执行命令级说明

### uv run uvicorn app.main:app --reload --port 8000
    
    uv run：在项目的虚拟环境里运行命令（等价于 npm run）
    uvicorn app.main:app：启动 app/main.py 里的 app 对象
    --reload：代码改动后自动重启，等价于 nodemon
    --port 8000：监听 8000 端口

### 启动代码
    uv run uvicorn app.main:app --reload --port 8000