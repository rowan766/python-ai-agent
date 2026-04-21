<template>
  <div class="chat-page">
    <!-- 左侧：文档选择 + 快捷问题 + 对话历史 -->
    <aside class="chat-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <template v-if="!sidebarCollapsed">
          <h3><el-icon><DocumentCopy /></el-icon> 文档知识库</h3>
        </template>
        <template v-else>
          <h3 class="sidebar-title-collapsed"><el-icon :size="18"><DocumentCopy /></el-icon></h3>
        </template>
        <button class="sidebar-toggle" @click="toggleSidebar" :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'">
          <el-icon v-if="sidebarCollapsed"><Expand /></el-icon>
          <el-icon v-else><Fold /></el-icon>
        </button>
      </div>

      <div v-show="!sidebarCollapsed" class="sidebar-body">
        <div class="sidebar-section">
          <label class="section-label">知识空间</label>
          <el-select
            v-model="selectedSpaceId"
            clearable
            filterable
            placeholder="默认检索全部可见空间"
            size="small"
            class="doc-select"
            @change="handleSpaceChange"
          >
            <el-option
              v-for="item in knowledgeSpaceOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </div>

        <!-- 文档范围选择（多选） -->
        <div class="sidebar-section">
          <label class="section-label">限定文档</label>
          <el-select
            v-model="selectedDocIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            placeholder="默认检索全部可见文档"
            size="small"
            class="doc-select"
          >
            <el-option
              v-for="item in documentOptions"
              :key="item.id"
              :label="item.title"
              :value="item.id"
            >
              <span>{{ item.title }}</span>
              <span style="color: #999; font-size: 12px; margin-left: auto;">{{ item.chunkCount || 0 }} 切片</span>
            </el-option>
          </el-select>
        </div>

        <!-- 操作按钮 -->
        <div class="sidebar-actions">
          <el-button type="primary" plain size="small" @click="handleNewChat">
            <el-icon><RefreshRight /></el-icon> 新建对话
          </el-button>
        </div>

        <!-- 历史对话记录 -->
        <div v-if="chatSessions.length" class="sidebar-section sidebar-sessions">
          <label class="section-label">历史记录</label>
          <div class="sessions-list">
            <div
              v-for="session in sortedSessions"
              :key="session.id"
              class="session-item"
              :class="{ active: currentSessionId === session.id }"
              @click="switchSession(session.id)"
            >
              <span class="session-title">{{ session.title || '新对话' }}</span>
              <span class="session-time">{{ formatSessionTime(session.updatedAt) }}</span>
              <button class="session-delete" title="删除此对话" @click.stop="deleteSession(session.id)">
                <el-icon :size="13"><Delete /></el-icon>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 折叠状态：只显示图标 -->
      <div v-if="sidebarCollapsed" class="sidebar-collapsed-body">
        <button class="collapsed-btn" title="新建对话" @click="handleNewChat">
          <el-icon :size="18"><RefreshRight /></el-icon>
        </button>
        <button class="collapsed-btn" title="历史记录" @click="sidebarCollapsed = false">
          <el-icon :size="18"><Clock /></el-icon>
        </button>
      </div>
    </aside>

    <!-- 主聊天区域 -->
    <main class="chat-main">
      <div class="chat-messages" ref="messagesRef">
        <!-- 空状态 -->
        <div v-if="!messages.length && !loading" class="chat-empty">
          <div class="empty-icon"><el-icon :size="48"><ChatDotRound /></el-icon></div>
          <h2>文档智能问答</h2>
          <p>基于当前有权限访问的文档切片进行 RAG 智能问答，支持多轮对话与上下文记忆。</p>
        </div>

        <!-- 消息列表 -->
        <template v-else>
          <div
            v-for="(msg, idx) in messages"
            :key="msg.uid"
            class="message-row"
            :class="msg.role"
          >
            <div class="message-avatar">
              <div class="avatar-icon" :class="msg.role">
                <el-icon v-if="msg.role === 'user'"><User /></el-icon>
                <el-icon v-else><Monitor /></el-icon>
              </div>
            </div>

            <div class="message-body">
              <div class="message-header">
                <span class="sender-name">{{ msg.role === 'user' ? '你' : '助手' }}</span>
                <span class="msg-meta">
                  <template v-if="msg.role === 'assistant'">
                    <el-tag v-if="msg.answerMode === 'llm-rag'" type="primary" effect="plain" size="small">{{ msg.answerModel || 'LLM' }}</el-tag>
                    <el-tag v-else type="info" effect="plain" size="small">检索摘要</el-tag>
                    <span v-if="msg.sources?.length" class="source-count">{{ msg.sources.length }} 条来源</span>
                  </template>
                  <span v-else class="msg-time">{{ formatTime(msg.timestamp) }}</span>
                </span>
                <button v-if="!loading" class="msg-delete-btn" title="删除消息" @click.stop="deleteMessage(idx)">
                  <el-icon :size="14"><Close /></el-icon>
                </button>
              </div>

              <!-- 用户消息内容 -->
              <div v-if="msg.role === 'user'" class="message-content user-content">
                {{ msg.content }}
              </div>

              <!-- 助手消息（Markdown 渲染） -->
              <div v-else class="message-content assistant-content">
                <div v-if="isLoadingLast(idx)" class="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
                <div v-else class="answer-md" v-html="renderMarkdown(msg.content)"></div>

                <!-- 来源引用折叠区（默认收起） -->
                <div v-if="hasSources(msg, idx)" class="sources-inline">
                  <button class="sources-toggle" @click="toggleSources(msg)">
                    <el-icon><DocumentCopy /></el-icon>
                    引用来源 {{ msg._sourcesExpanded ? '\u25BC' : '\u25B6' }}
                    ({{ msg.sources.length }})
                  </button>
                  <transition name="slide">
                    <div v-show="msg._sourcesExpanded" class="sources-list">
                      <div
                        v-for="(src, si) in msg.sources"
                        :key="`${src.chunkId}-${si}-${idx}`"
                        class="source-item"
                        @click="openSourcePreview(src)"
                      >
                        <div class="source-item__header">
                          <strong>{{ src.documentTitle || `文档 #${src.documentId}` }}</strong>
                          <span v-if="src.spaceName" class="source-item__space">{{ src.spaceName }}</span>
                          <span class="source-item__score">{{ Number(src.score || 0).toFixed(4) }}</span>
                          <span class="source-item__index">切片 {{ src.chunkIndex ?? '-' }}</span>
                        </div>
                        <p class="source-item__preview">{{ getSourcePreview(src.content) }}</p>
                      </div>
                    </div>
                  </transition>
                </div>

                <!-- AI 追问建议 -->
                <div v-if="msg.suggestions?.length && !isLoadingLast(idx)" class="follow-up-suggestions">
                  <button
                    v-for="(sug, si) in msg.suggestions"
                    :key="`sug-${msg.uid}-${si}`"
                    class="suggestion-chip"
                    @click="handleQuickPrompt(sug)"
                  >{{ sug }}</button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- 底部输入区 -->
      <div class="chat-input-area">
        <div class="input-container">
          <textarea
            ref="inputRef"
            v-model="inputText"
            class="chat-textarea"
            rows="1"
            :placeholder="loading ? '\u6B63\u5728\u601D\u8003\u4E2D...' : '\u8F93\u5165\u4F60\u7684\u95EE\u9898...'"
            :disabled="loading"
            @keydown.enter.exact.prevent="handleSubmit"
            @input="autoResizeTextarea"
          ></textarea>
          <button
            class="send-btn"
            :disabled="!inputText.trim() || loading"
            @click="handleSubmit"
          >
            <el-icon v-if="!loading"><Promotion /></el-icon>
            <el-icon v-else class="spin-loading"><Loading /></el-icon>
          </button>
        </div>
        <p class="input-hint">Enter \u53D1\u9001 &middot; \u57FA\u4E8E RAG \u68C0\u7D22\u589E\u5F03\u751F\u6210 &middot; \u652F\u6301\u591A\u8F6E\u4E0A\u4e0b\u6587\u8BB0\u5FC6</p>
      </div>
    </main>

    <!-- 来源全文弹窗 -->
    <el-dialog v-model="previewVisible" title="\u6765\u6E90\u5207\u7247\u5168\u6587" width="720px" destroy-on-close>
      <div v-if="activeSource" class="source-preview-dialog">
        <div class="sp-meta">
          <span>{{ activeSource.documentTitle || `\u6587\u6863 #${activeSource.documentId}` }}</span>
          <em v-if="activeSource.spaceName">\u7A7A\u95F4 {{ activeSource.spaceName }}</em>
          <em>\u5207\u7247 {{ activeSource.chunkIndex ?? '-' }}</em>
          <em>\u5F97\u5206 {{ Number(activeSource.score || 0).toFixed(4) }}</em>
        </div>
        <el-scrollbar max-height="450px">
          <pre class="sp-text">{{ activeSource.content }}</pre>
        </el-scrollbar>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Clock,
  Close,
  Delete,
  DocumentCopy,
  Expand,
  Fold,
  Loading,
  Monitor,
  Promotion,
  RefreshRight,
  User,
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import { API_BASE_URL } from '../../utils/api-base-url'
import {
  askDocumentQuestion,
  createDocumentQaSession,
  deleteDocumentQaMessage,
  deleteDocumentQaSession,
  getDocumentList,
  getDocumentQaSessions,
  syncDocumentQaSession,
  updateDocumentQaSession,
} from '../../api/document'
import { getKnowledgeSpaceList } from '../../api/knowledge-space'

// ---- Markdown 配置 ----
marked.setOptions({
  breaks: true,
  gfm: true,
})

// ---- Constants ----
let uidCounter = 0
const makeUid = () => `msg-${Date.now()}-${++uidCounter}`

const sidebarCollapsed = ref(false)
const selectedSpaceId = ref(null)
const selectedDocIds = ref([])
const knowledgeSpaceOptions = ref([])
const documentOptions = ref([])
const inputText = ref('')
const loading = ref(false)
const messages = ref([])
const messagesRef = ref(null)
const inputRef = ref(null)
const previewVisible = ref(false)
const activeSource = ref(null)
let lastExitPersistKey = ''

// ---- Session management (database persistence) ----
const currentSessionId = ref(null)
const chatSessions = ref([])

const toMillis = (value) => {
  if (!value) return 0
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? 0 : time
}

const normalizeMessage = (message = {}) => ({
  id: message.id ?? null,
  uid: makeUid(),
  role: message.role,
  content: message.content || '',
  timestamp: message.timestamp || message.createdAt || Date.now(),
  answerMode: message.answerMode || '',
  answerModel: message.answerModel || '',
  sources: Array.isArray(message.sources) ? message.sources : [],
  suggestions: Array.isArray(message.suggestions) ? message.suggestions : [],
  _sourcesExpanded: false,
})

const normalizeSession = (session = {}) => ({
  id: session.id,
  title: session.title || '',
  messages: Array.isArray(session.messages) ? session.messages.map(normalizeMessage) : [],
  createdAt: session.createdAt || '',
  updatedAt: session.updatedAt || '',
  spaceId: Number.isInteger(Number(session.spaceId)) && Number(session.spaceId) > 0 ? Number(session.spaceId) : null,
  docIds: Array.isArray(session.docIds)
    ? session.docIds.map(item => Number(item)).filter(item => Number.isInteger(item) && item > 0)
    : [],
})

const sortedSessions = computed(() => {
  return [...chatSessions.value].sort((a, b) => toMillis(b.updatedAt) - toMillis(a.updatedAt))
})

const availableDocumentIdSet = computed(() => {
  return new Set(
    documentOptions.value
      .map(item => Number(item?.id))
      .filter(item => Number.isInteger(item) && item > 0),
  )
})

const getScopedDocIds = () => {
  const validDocIds = selectedDocIds.value
    .map(item => Number(item))
    .filter(item => Number.isInteger(item) && item > 0 && availableDocumentIdSet.value.has(item))

  return validDocIds.length > 0 ? validDocIds : []
}

const applyCurrentSession = (session) => {
  currentSessionId.value = session?.id ?? null
  messages.value = Array.isArray(session?.messages) ? session.messages.map(normalizeMessage) : []
  selectedSpaceId.value = session?.spaceId ?? null
  selectedDocIds.value = Array.isArray(session?.docIds) ? [...session.docIds] : []
}

const upsertSession = (session) => {
  const normalized = normalizeSession(session)
  const idx = chatSessions.value.findIndex(item => item.id === normalized.id)
  if (idx >= 0) {
    chatSessions.value[idx] = normalized
  } else {
    chatSessions.value.push(normalized)
  }
  return normalized
}

const serializeMessages = () => {
  return messages.value.map(msg => ({
    role: msg.role,
    content: msg.content,
    timestamp: msg.timestamp || null,
    answerMode: msg.answerMode || null,
    answerModel: msg.answerModel || null,
    sources: msg.sources || [],
    suggestions: msg.suggestions || [],
  }))
}

const buildSessionPayload = () => ({
  title: getSessionTitle(),
  spaceId: selectedSpaceId.value || undefined,
  docIds: getScopedDocIds(),
  messages: serializeMessages(),
})

const loadSessions = async () => {
  const res = await getDocumentQaSessions()
  const payload = res?.data ?? res ?? []
  chatSessions.value = Array.isArray(payload) ? payload.map(normalizeSession) : []
}

const ensureCurrentSession = async () => {
  if (currentSessionId.value) return currentSessionId.value
  const res = await createDocumentQaSession({
    spaceId: selectedSpaceId.value || undefined,
    docIds: getScopedDocIds(),
  })
  const session = res?.data ?? res ?? null
  if (!session?.id) {
    throw new Error('创建对话失败')
  }
  const normalized = upsertSession(session)
  applyCurrentSession(normalized)
  return normalized.id
}

const saveCurrentSession = async () => {
  if (!currentSessionId.value && !messages.value.length) return
  const sessionId = await ensureCurrentSession()
  const payload = buildSessionPayload()
  const res = messages.value.length
    ? await syncDocumentQaSession(sessionId, payload)
    : await updateDocumentQaSession(sessionId, { title: payload.title, spaceId: payload.spaceId, docIds: payload.docIds })

  const session = res?.data ?? res ?? null
  if (!session?.id) return
  const normalized = upsertSession(session)
  if (currentSessionId.value === normalized.id) {
    applyCurrentSession(normalized)
  }
}

const persistCurrentSessionOnPageExit = () => {
  if (!currentSessionId.value) return

  const token = localStorage.getItem('token')
  if (!token) return

  const payload = buildSessionPayload()
  const hasMessages = payload.messages.length > 0
  const requestUrl = hasMessages
    ? `${API_BASE_URL}/document/qa/sessions/${currentSessionId.value}/sync`
    : `${API_BASE_URL}/document/qa/sessions/${currentSessionId.value}`
  const requestBody = JSON.stringify(
    hasMessages
      ? payload
      : { title: payload.title, spaceId: payload.spaceId, docIds: payload.docIds },
  )
  const persistKey = `${currentSessionId.value}:${requestBody}`
  if (persistKey === lastExitPersistKey) return
  lastExitPersistKey = persistKey

  void fetch(requestUrl, {
    method: hasMessages ? 'PUT' : 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: requestBody,
    keepalive: true,
  }).catch(() => {})
}

const handleVisibilityChange = () => {
  if (document.visibilityState === 'hidden') {
    persistCurrentSessionOnPageExit()
  }
}

const handlePageHide = () => {
  persistCurrentSessionOnPageExit()
}

const switchSession = async (id, options = {}) => {
  const { skipSave = false } = options
  if (!skipSave) {
    await saveCurrentSession()
  }

  const session = chatSessions.value.find(item => item.id === id)
  if (!session) return

  applyCurrentSession(session)
  await fetchDocuments()
  await scrollToBottom()
}

const deleteSession = async (id) => {
  try {
    await ElMessageBox.confirm('\u786E\u5B9A\u5220\u9664\u6B64\u5BF9\u8BDD\u5417\uFF1F', '\u63D0\u793A', {
      confirmButtonText: '\u786E\u5B9A',
      cancelButtonType: 'info',
      type: 'warning',
    })
  } catch { return }

  await deleteDocumentQaSession(id)
  chatSessions.value = chatSessions.value.filter(session => session.id !== id)

  if (currentSessionId.value === id) {
    const nextSession = sortedSessions.value[0]
    if (nextSession) {
      await switchSession(nextSession.id, { skipSave: true })
    } else {
      currentSessionId.value = null
      messages.value = []
      await scrollToBottom()
    }
  }
}

const handleNewChat = async () => {
  await saveCurrentSession()
  currentSessionId.value = null
  messages.value = []
  activeSource.value = null
}

const getSessionTitle = () => {
  const firstUserMsg = messages.value.find(m => m.role === 'user')
  if (firstUserMsg && firstUserMsg.content) {
    return firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '')
  }
  return ''
}

// ---- Message actions ----

const deleteMessage = async (idx) => {
  const msg = messages.value[idx]
  try {
    await ElMessageBox.confirm('\u786E\u5B9A\u5220\u9664\u6B64\u6D88\u606F\u5417\uFF1F', '\u63D0\u793A', {
      confirmButtonText: '\u786E\u5B9A',
      cancelButtonType: 'info',
      type: 'warning',
    })
  } catch { return }

  if (currentSessionId.value && msg?.id) {
    const res = await deleteDocumentQaMessage(currentSessionId.value, msg.id)
    const session = res?.data ?? res ?? null
    if (session?.id) {
      const normalized = upsertSession(session)
      applyCurrentSession(normalized)
    }
    return
  }

  if (msg.role === 'user') {
    const nextIdx = idx + 1
    if (nextIdx < messages.value.length && messages.value[nextIdx].role === 'assistant') {
      messages.value.splice(nextIdx, 1)
    }
  }
  messages.value.splice(idx, 1)
  if (currentSessionId.value) {
    await saveCurrentSession()
  }
}

// ---- UI helpers ----

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const fetchDocuments = async () => {
  try {
    const res = await getDocumentList({
      page: 1,
      pageSize: 200,
      status: 'success',
      spaceId: selectedSpaceId.value || undefined,
    })
    const payload = res?.data ?? res ?? {}
    documentOptions.value = payload.list || []
    const currentSession = currentSessionId.value
      ? chatSessions.value.find(item => item.id === currentSessionId.value)
      : null
    selectedDocIds.value = currentSession?.docIds?.length
      ? currentSession.docIds.filter(item => availableDocumentIdSet.value.has(item))
      : getScopedDocIds()
    if (currentSession) {
      currentSession.docIds = [...selectedDocIds.value]
    }
  } catch { /* ignore */ }
}

const fetchKnowledgeSpaces = async () => {
  try {
    const res = await getKnowledgeSpaceList({ page: 1, pageSize: 200, status: 1 })
    const payload = res?.data ?? res ?? {}
    knowledgeSpaceOptions.value = payload.list || []
  } catch {
    knowledgeSpaceOptions.value = []
  }
}

const handleSpaceChange = async () => {
  selectedDocIds.value = []
  await fetchDocuments()
  if (currentSessionId.value) {
    try {
      await saveCurrentSession()
    } catch {
      ElMessage.error('对话保存失败，请稍后重试')
    }
  }
}

const handleQuickPrompt = (text) => {
  inputText.value = text
  nextTick(() => inputRef.value?.focus())
}

const toggleSources = (msg) => {
  msg._sourcesExpanded = !msg._sourcesExpanded
}

const getSourcePreview = (content = '') => {
  const t = String(content).replace(/\s+/g, ' ').trim()
  return t.length <= 120 ? t : `${t.slice(0, 120)}...`
}

const openSourcePreview = (source) => {
  activeSource.value = source
  previewVisible.value = true
}

const scrollToBottom = async () => {
  await nextTick()
  const el = messagesRef.value
  if (el) el.scrollTop = el.scrollHeight
}

const autoResizeTextarea = () => {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const formatSessionTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()

  if (isToday) {
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return '\u6628\u5929'
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// ---- Computed helpers for template ----
const isLoadingLast = (idx) => loading.value && idx === messages.value.length - 1

const hasSources = (msg, idx) => {
  if (!msg.sources?.length) return false
  if (loading.value && idx === messages.value.length - 1) return false
  return true
}

const renderMarkdown = (content) => {
  if (!content) return ''
  try {
    return marked(content)
  } catch { return content.replace(/</g, '&lt;').replace(/>/g, '&gt;') }
}

// ---- Core logic ----

const buildHistory = () => {
  return messages.value
    .filter(m => m.role === 'user' || (m.role === 'assistant' && m.content))
    .map(m => ({ role: m.role, content: m.content }))
}

const handleSubmit = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  try {
    await ensureCurrentSession()
  } catch {
    ElMessage.error('创建对话失败，请稍后重试')
    return
  }

  // Append user message
  const userMsg = { uid: makeUid(), role: 'user', content: text, timestamp: Date.now() }
  messages.value.push(userMsg)

  inputText.value = ''
  autoResizeTextarea()

  try {
    await saveCurrentSession()
  } catch {
    ElMessage.error('对话保存失败，请稍后重试')
  }

  // Append placeholder assistant message
  const assistMsg = {
    uid: makeUid(),
    role: 'assistant',
    content: '',
    answerMode: '',
    answerModel: '',
    sources: [],
    _sourcesExpanded: false,
  }
  messages.value.push(assistMsg)
  loading.value = true
  await scrollToBottom()

  try {
    const history = buildHistory().slice(0, -1)
    const scopedDocIds = getScopedDocIds()
    const res = await askDocumentQuestion({
      question: text,
      limit: 4,
      spaceId: selectedSpaceId.value || undefined,
      documentIds: scopedDocIds.length > 0 ? scopedDocIds : undefined,
      history,
    })
    const data = res?.data || res || {}

    Object.assign(assistMsg, {
      content: data.answer || '',
      answerMode: data.answerMode || '',
      answerModel: data.answerModel || '',
      sources: data.sources || [],
      suggestions: data.suggestions || [],
      timestamp: Date.now(),
    })
  } catch {
    Object.assign(assistMsg, {
      content: '\u62B1\u6B49\uFF0C\u56DE\u7B54\u751F\u6210\u8FC7\u7A0B\u4E2D\u51FA\u73B0\u4E86\u9519\u8BEF\uFF0C\u8BF7\u7A0D\u540E\u91CD\u8BD5\u3002',
      answerMode: 'error',
      sources: [],
    })
  } finally {
    loading.value = false
    await scrollToBottom()
    try {
      await saveCurrentSession()
    } catch {
      ElMessage.error('对话保存失败，请稍后重试')
    }
  }
}

// ---- Lifecycle ----
onMounted(async () => {
  await fetchKnowledgeSpaces()
  await loadSessions()
  if (sortedSessions.value.length > 0) {
    await switchSession(sortedSessions.value[0].id, { skipSave: true })
  } else {
    await fetchDocuments()
  }
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('pagehide', handlePageHide)
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('pagehide', handlePageHide)
  persistCurrentSessionOnPageExit()
})
</script>

<style scoped>
.chat-page {
  display: flex;
  height: calc(100vh - 84px);
  background: #f8fafc;
  overflow: hidden;
  border-radius: 20px;
}

/* ===== Sidebar ===== */
.chat-sidebar {
  width: 280px;
  min-width: 280px;
  background: #fff;
  border-right: 1px solid #e8ecf2;
  display: flex;
  flex-direction: column;
  transition: min-width 0.28s ease, width 0.28s ease;
}
.chat-sidebar.collapsed {
  width: 52px;
  min-width: 52px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 14px 14px;
  border-bottom: 1px solid #f0f2f7;
  gap: 6px;
}
.sidebar-header h3 {
  font-size: 15px;
  color: #1f2937;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  overflow: hidden;
  flex: 1;
}
.sidebar-header h3.sidebar-title-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.sidebar-toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  color: #6b7a90;
  flex-shrink: 0;
}
.sidebar-toggle:hover { background: #f1f5f9; }

.sidebar-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Collapsed body */
.sidebar-collapsed-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 16px 0;
}
.collapsed-btn {
  background: none;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  color: #64748b;
  padding: 8px;
  transition: all 0.18s;
}
.collapsed-btn:hover { background: #f1f5f9; color: #3b82f6; border-color: #bfdbfe; }

/* Sidebar sections */
.sidebar-section { display: flex; flex-direction: column; gap: 8px; }
.section-label {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.doc-select { width: 100%; }
.doc-select :deep(.el-input__wrapper) {
  max-height: 80px;
  overflow-y: auto;
}
.doc-select :deep(.el-select__tags-text) {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Follow-up suggestions */
.follow-up-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f0f2f7;
}
.suggestion-chip {
  font-size: 13px;
  color: #3b82f6;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  padding: 5px 14px;
  cursor: pointer;
  transition: all 0.18s;
  white-space: nowrap;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.suggestion-chip:hover {
  background: #dbeafe;
  border-color: #93c5fd;
}

.sidebar-actions { margin-top: auto; }

/* Sessions list */
.sidebar-sessions { flex: 1; min-height: 0; }
.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 240px;
  overflow-y: auto;
}
.session-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
  position: relative;
}
.session-item:hover { background: #f8fafc; }
.session-item.active {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.session-title {
  flex: 1;
  font-size: 12px;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-time {
  font-size: 11px;
  color: #94a3b8;
  flex-shrink: 0;
}
.session-delete {
  background: none;
  border: none;
  opacity: 0;
  cursor: pointer;
  color: #cbd5e1;
  padding: 2px;
  border-radius: 4px;
  flex-shrink: 0;
  transition: all 0.15s;
}
.session-item:hover .session-delete { opacity: 1; }
.session-delete:hover { color: #ef4444; background: #fef2f2; }

/* ===== Main Chat Area ===== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

/* Messages scroll area */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px 16px;
  scroll-behavior: smooth;
}

/* Empty state */
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  gap: 10px;
}
.empty-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
  margin-bottom: 6px;
}
.chat-empty h2 { font-size: 22px; color: #1e293b; margin: 0; }
.chat-empty p { font-size: 14px; color: #94a3b8; margin: 0; max-width: 420px; line-height: 1.6; }

/* Message row */
.message-row {
  display: flex;
  gap: 14px;
  margin-bottom: 24px;
  animation: fadeInUp 0.3s ease both;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-avatar { flex-shrink: 0; padding-top: 2px; }

.avatar-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
}
.avatar-icon.user {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
}
.avatar-icon.assistant {
  background: linear-gradient(135deg, #06b6d4, #0891b2);
  color: #fff;
}

.message-body { flex: 1; min-width: 0; }
.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.sender-name {
  font-weight: 600;
  font-size: 13px;
  color: #334155;
}
.msg-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
}
.source-count { font-size: 11px; color: #64748b; }
.msg-time { font-size: 11px; }

.msg-delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #c0c4cc;
  padding: 4px;
  border-radius: 6px;
  margin-left: 8px;
  flex-shrink: 0;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.message-row:hover .msg-delete-btn { color: #94a3b8; }
.msg-delete-btn:hover { color: #ef4444 !important; background: #fef2f2; }

.message-content { word-break: break-word; }

.user-content {
  background: #f1f5f9;
  padding: 12px 16px;
  border-radius: 4px 14px 14px 14px;
  font-size: 14px;
  line-height: 1.7;
  color: #1e293b;
  display: inline-block;
  max-width: 85%;
}

.assistant-content {
  font-size: 14px;
  color: #334155;
}

/* Markdown rendered answer */
.answer-md {
  padding: 12px 0;
  line-height: 1.85;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
.answer-md :deep(p) { margin: 0 0 8px; }
.answer-md :deep(p:last-child) { margin-bottom: 0; }
.answer-md :deep(h1), .answer-md :deep(h2), .answer-md :deep(h3),
.answer-md :deep(h4), .answer-md :deep(h5), .answer-md :deep(h6) {
  margin: 14px 0 8px;
  font-weight: 600;
  line-height: 1.35;
}
.answer-md :deep(h1) { font-size: 1.25em; }
.answer-md :deep(h2) { font-size: 1.15em; }
.answer-md :deep(h3) { font-size: 1.08em; }
.answer-md :deep(ul), .answer-md :deep(ol) { margin: 8px 0; padding-left: 20px; }
.answer-md :deep(li) { margin-bottom: 3px; line-height: 1.7; }
.answer-md :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 14px;
  border-left: 3px solid #93c5fd;
  background: #f8fafc;
  border-radius: 0 8px 8px 0;
  color: #475569;
}
.answer-md :deep(code) {
  padding: 2px 6px;
  background: #f1f5f9;
  border-radius: 4px;
  font-size: 0.89em;
  color: #db2777;
}
.answer-md :deep(pre) {
  margin: 8px 0;
  padding: 14px 16px;
  background: #1e293b;
  border-radius: 10px;
  overflow-x: auto;
}
.answer-md :deep(pre code) {
  padding: 0;
  background: none;
  color: #e2e8f0;
  font-size: 13px;
  line-height: 1.6;
}
.answer-md :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}
.answer-md :deep(th), .answer-md :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 7px 12px;
  text-align: left;
}
.answer-md :deep(th) { background: #f8fafc; font-weight: 600; }
.answer-md :deep(strong) { font-weight: 600; color: #1e293b; }
.answer-md :deep(a) { color: #2563eb; text-decoration: underline; }
.answer-md :deep(hr) { border: none; border-top: 1px solid #e2e8f0; margin: 14px 0; }

/* Typing indicator */
.typing-indicator {
  display: flex;
  gap: 5px;
  padding: 12px 0;
}
.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  animation: bounce 1.4s infinite both;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.16s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.32s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.65); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.spin-loading { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Sources inline */
.sources-inline { margin-top: 12px; }
.sources-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.18s;
}
.sources-toggle:hover { background: #f8fafc; border-color: #cbd5e1; }

.sources-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.source-item {
  padding: 10px 12px;
  border: 1px solid #e8ecf2;
  border-radius: 10px;
  background: #fbfdff;
  cursor: pointer;
  transition: all 0.16s;
}
.source-item:hover { border-color: #bfdbfe; background: #f0f7ff; }
.source-item__header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: #64748b;
  margin-bottom: 4px;
}
.source-item__header strong { color: #1e293b; font-size: 12px; }
.source-item__space {
  padding: 1px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
}
.source-item__score { margin-left: auto; }
.source-item__preview {
  margin: 0;
  font-size: 12px;
  color: #475569;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.22s ease;
  overflow: hidden;
}
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-6px); max-height: 0; }

/* Input area */
.chat-input-area {
  padding: 14px 28px 18px;
  border-top: 1px solid #e8ecf2;
  background: #fff;
}
.input-container {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 8px 12px;
  transition: border-color 0.2s;
}
.input-container:focus-within { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }

.chat-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.55;
  color: #1e293b;
  font-family: inherit;
  max-height: 160px;
  padding: 4px 0;
}
.chat-textarea::placeholder { color: #cbd5e1; }
.chat-textarea:disabled { cursor: wait; }

.send-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: none;
  background: #3b82f6;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 18px;
  transition: all 0.18s;
}
.send-btn:hover:not(:disabled) { background: #2563eb; transform: scale(1.05); }
.send-btn:disabled { background: #cbd5e1; cursor: not-allowed; }

.input-hint {
  text-align: center;
  font-size: 11px;
  color: #c4d0dc;
  margin: 8px 0 0;
}

/* Source dialog */
.source-preview-dialog { display: flex; flex-direction: column; gap: 12px; }
.sp-meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #64748b;
  flex-wrap: wrap;
}
.sp-text {
  margin: 0;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  color: #334155;
  font-size: 14px;
  background: #f8fafc;
  border-radius: 10px;
}

/* Responsive */
@media (max-width: 900px) {
  .chat-sidebar { display: none; }
  .chat-messages { padding: 16px; }
  .chat-input-area { padding: 10px 14px 14px; }
}
</style>
