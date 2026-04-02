# 负责读取 文本或文本并切分成小块


from langchain_community.document_loaders import (
    PyPDFLoader,        # PDF
    TextLoader,         # .txt / .md
    Docx2txtLoader,     # Word .docx
    UnstructuredExcelLoader,    # Excel .xlsx
    UnstructuredPowerPointLoader,  # PPT .pptx
    UnstructuredHTMLLoader,     # HTML
    UnstructuredMarkdownLoader, # Markdown
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from typing import List
from langchain_core.documents import Document

# 文本切分器：把长文档切成小块，方便向量化检索
# chunk_size=500：每块约500字符（中文约250个字）
# chunk_overlap=50：相邻块重叠50字符，避免语义在边界被截断
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", " ", ""]
)

# 支持的文件格式映射表
SUPPORTED_EXTENSIONS = {
    ".pdf":  PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".doc":  Docx2txtLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".xls":  UnstructuredExcelLoader,
    ".pptx": UnstructuredPowerPointLoader,
    ".ppt":  UnstructuredPowerPointLoader,
    ".html": UnstructuredHTMLLoader,
    ".htm":  UnstructuredHTMLLoader,
    ".md":   UnstructuredMarkdownLoader,
    ".txt":  TextLoader,
}

def load_documents(file_path: str) -> List[Document]:
    """
    根据文件扩展名自动选择合适的解析器加载文档，
    然后切分成小块返回。
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(SUPPORTED_EXTENSIONS.keys())
        raise ValueError(f"不支持的文件格式: {ext}，当前支持: {supported}")

    loader_class = SUPPORTED_EXTENSIONS[ext]

    # TextLoader 需要指定编码，其他 loader 不需要
    if loader_class is TextLoader:
        loader = loader_class(str(path), encoding="utf-8")
    else:
        loader = loader_class(str(path))

    docs = loader.load()
    return text_splitter.split_documents(docs)


def get_supported_formats() -> List[str]:
    """返回支持的文件格式列表（供接口展示用）"""
    return list(SUPPORTED_EXTENSIONS.keys())