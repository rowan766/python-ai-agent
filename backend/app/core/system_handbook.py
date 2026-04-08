from dataclasses import dataclass
import re


@dataclass(frozen=True)
class HandbookSection:
    key: str
    title: str
    keywords: tuple[str, ...]
    content: str
    priority: int = 0


SECTIONS: tuple[HandbookSection, ...] = (
    HandbookSection(
        key="overview",
        title="系统总览",
        keywords=("系统", "平台", "应用", "菜单", "导航", "模块", "介绍", "怎么用"),
        priority=100,
        content=(
            "这是一个带组织权限的企业知识平台。登录后，如果用户还没有部门归属，会先进入“组织接入”页面 "
            "(`/onboarding`)；完成接入后，左侧菜单包含“工作台”(`/workspace`)、“知识空间”(`/knowledge-bases`)、"
            "“文档中心”(`/documents`)、“上传文档”(`/documents/upload`)、“知识检索”(`/knowledge/search`)、"
            "“AI 对话”(`/ai/chat`)、“审批中心”(`/approvals`)、“组织与部门”(`/organization`)。"
            "平台管理员额外可见“用户管理”(`/users`)。页面顶部会展示当前工作部门，多个部门归属用户可以切换部门视角。"
        ),
    ),
    HandbookSection(
        key="workspace",
        title="工作台",
        keywords=("工作台", "workspace", "首页", "概览", "待办", "快捷入口"),
        content=(
            "工作台页面路径是 `/workspace`。页面顶部显示当前部门和快捷入口；摘要卡片展示“当前部门”、“可访问知识空间”、"
            "“可访问文档”、“待处理审批”。下方表格包含“我的部门”、“快捷入口”、“待办概览”、“我发起的事项”。"
            "它适合回答用户当前能访问什么、有哪些待办、应该从哪里继续处理工作。"
        ),
    ),
    HandbookSection(
        key="knowledge_bases",
        title="知识空间",
        keywords=("知识空间", "空间", "知识库", "共享", "新建空间", "创建空间"),
        content=(
            "知识空间页面路径是 `/knowledge-bases`。用户可以按部门筛选可见空间，查看空间名称、编码、归属部门、文档数、"
            "可见范围和已共享目标。点击“新建空间”会弹出表单，填写归属部门、空间名称、空间编码和默认可见范围后创建。"
            "点击行内“文档”可跳转文档中心，点击“上传”可跳转上传文档页，点击“共享”可发起跨部门共享申请。"
            "创建知识空间需要目标部门负责人或平台管理员权限。"
        ),
    ),
    HandbookSection(
        key="documents",
        title="文档中心与上传",
        keywords=("文档", "上传", "文件", "下载", "删除", "切片", "文档中心"),
        content=(
            "文档中心路径是 `/documents`，支持按部门和知识空间筛选，列表会显示文档标题、文件名、知识空间、归属部门、"
            "上传人、切片数、可见范围和文件格式，并提供下载、删除操作。上传文档页路径是 `/documents/upload`，"
            "用于把文件上传到指定知识空间，并完成解析、切片和向量索引。上传前通常先确定目标知识空间。"
        ),
    ),
    HandbookSection(
        key="search_and_chat",
        title="知识检索与AI对话",
        keywords=("知识检索", "ai", "对话", "聊天", "rag", "搜索", "问答"),
        content=(
            "“知识检索”页面路径是 `/knowledge/search`，更偏向显式检索知识片段；“AI 对话”页面路径是 `/ai/chat`，"
            "更偏向自然语言助手。AI 对话会复用当前系统登录状态，并带入当前用户、部门视角、可访问知识和系统手册上下文。"
            "因此它既能回答“这个系统怎么用”，也能回答“我当前能看到什么、该去哪里操作”。"
        ),
    ),
    HandbookSection(
        key="approvals",
        title="审批中心",
        keywords=("审批", "待办", "通过", "驳回", "申请", "审批中心"),
        content=(
            "审批中心路径是 `/approvals`。这里统一处理两类事项：组织加入申请和知识空间共享申请。"
            "页面摘要会显示待处理总数、组织申请数、共享申请数、我发起事项数。主体区域分成四类列表："
            "待我处理的组织申请、待我处理的共享申请、我发起的组织申请、我发起的共享申请。"
            "部门负责人或平台管理员可以在这里执行通过与驳回。"
        ),
    ),
    HandbookSection(
        key="onboarding",
        title="组织接入",
        keywords=("组织接入", "加入部门", "onboarding", "待归属", "首个部门", "入驻"),
        content=(
            "组织接入页面路径是 `/onboarding`。如果系统还没有任何部门，首位用户可以初始化首个部门，并自动成为负责人；"
            "如果系统已有部门但当前用户尚未归属，可在这里发起加入部门申请；如果用户已经有部门归属，则页面会展示当前归属和申请记录。"
            "系统未完成组织接入时，其他业务页面会被路由守卫拦回这里。"
        ),
    ),
    HandbookSection(
        key="organization",
        title="组织与部门",
        keywords=("组织", "部门", "归属", "协作部门", "部门树", "负责人"),
        content=(
            "“组织与部门”页面路径是 `/organization`，主要用于查看我的组织身份、主归属部门、部门树以及发起协作部门申请。"
            "“部门治理”页面路径是 `/departments`，用于管理部门树、查看影响范围、查看部门成员、编辑部门信息、调整负责人和层级。"
            "部门治理更偏向负责人和管理员的治理操作，组织与部门更偏向普通用户查看归属和申请协作关系。"
        ),
    ),
    HandbookSection(
        key="users",
        title="用户管理",
        keywords=("用户管理", "用户", "启用", "禁用", "平台管理员", "账号"),
        content=(
            "用户管理页面路径是 `/users`，只有平台管理员可见。这里用于查看用户列表、筛选状态、调整部门归属、设置主部门、"
            "启用或禁用账号。和部门审批链相关的负责人调整，也需要结合用户管理与部门治理一起完成。"
        ),
    ),
)


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip().lower())


def _score_section(query: str, section: HandbookSection) -> int:
    score = section.priority
    for keyword in section.keywords:
        if keyword.lower() in query:
            score += max(1, len(keyword))
    return score


def get_relevant_handbook_sections(query: str, limit: int = 4) -> list[HandbookSection]:
    normalized_query = _normalize_query(query)
    overview_section = next(section for section in SECTIONS if section.key == "overview")

    if not normalized_query:
        default_keys = {"workspace", "knowledge_bases", "documents"}
        default_sections = [section for section in SECTIONS if section.key in default_keys]
        return [overview_section, *default_sections[: max(limit - 1, 0)]]

    scored_sections = sorted(
        (
            (_score_section(normalized_query, section), section)
            for section in SECTIONS
            if section.key != "overview"
        ),
        key=lambda item: item[0],
        reverse=True,
    )

    matched_sections = [section for score, section in scored_sections if score > 0][: max(limit - 1, 0)]
    if not matched_sections:
        matched_sections = [section for section in SECTIONS if section.key in {"workspace", "knowledge_bases"}]

    return [overview_section, *matched_sections]


def build_system_handbook_context(query: str) -> str:
    sections = get_relevant_handbook_sections(query)
    lines = [
        "以下是系统功能说明与页面导航，回答“这个系统怎么用、去哪里操作、页面里有什么信息”时优先参考：",
    ]
    for section in sections:
        lines.append(f"[{section.title}] {section.content}")
    lines.append("回答系统操作问题时，请优先说明页面名称、路径和关键操作按钮；不要虚构不存在的页面。")
    return "\n".join(lines)
