<script setup lang="ts">
import axios from 'axios'
import { Plus } from '@element-plus/icons-vue'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { fetchKnowledgeBases } from '@/api/modules/knowledge'
import { queryKnowledge, streamChat } from '@/api/modules/rag'
import type { KnowledgeBaseItem } from '@/types/knowledge'
import type { ChatMessage, SearchResponse } from '@/types/rag'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

interface ChatSession {
  id: string
  title: string
  updatedAt: number
  messages: ChatMessage[]
}

const route = useRoute()
const loading = ref(false)
const response = ref<SearchResponse | null>(null)
const knowledgeBases = ref<KnowledgeBaseItem[]>([])

const searchForm = reactive({
  query: 'Agent',
  limit: 5,
  knowledgeBaseId: undefined as number | undefined,
})

const chatForm = reactive({
  input: '',
  model: 'qwen-turbo',
})

const conversations = ref<ChatSession[]>([])
const currentConversationId = ref('')
const chatLoading = ref(false)
const chatAbortController = ref<AbortController | null>(null)

const quickQueries = ['Agent', 'FastAPI', 'Qdrant', 'upload test document']
const quickPrompts = [
  '帮我总结一下这个平台当前支持的核心能力',
  '如果我是部门负责人，应该如何搭建知识库空间',
  '帮我解释一下文档上传到向量库之后发生了什么',
]

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const isChatMode = computed(() => route.name === 'ai-chat')
const currentConversation = computed(() =>
  conversations.value.find((item) => item.id === currentConversationId.value) ?? null,
)
const pageTitle = computed(() =>
  isChatMode.value ? currentConversation.value?.title || '新对话' : '知识检索',
)
const pageSubtitle = computed(() =>
  isChatMode.value ? '连续对话' : '按知识库范围检索文档片段',
)

function createConversation(title = '新对话'): ChatSession {
  const session: ChatSession = {
    id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    title,
    updatedAt: Date.now(),
    messages: [],
  }
  conversations.value = [session, ...conversations.value]
  currentConversationId.value = session.id
  return session
}

function ensureConversation(): ChatSession {
  return currentConversation.value ?? createConversation()
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message
  }

  return fallback
}

async function loadKnowledgeBaseOptions() {
  try {
    const result = await fetchKnowledgeBases()
    knowledgeBases.value = result.items
  } catch (error) {
    console.error(error)
  }
}

async function handleSearch() {
  if (!searchForm.query.trim()) {
    ElMessage.warning('请输入检索关键词。')
    return
  }

  loading.value = true
  try {
    response.value = await queryKnowledge(
      searchForm.query.trim(),
      searchForm.limit,
      searchForm.knowledgeBaseId,
    )
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '检索失败，请确认后端服务和向量检索状态。'))
    console.error(error)
  } finally {
    loading.value = false
  }
}

function applyQuickQuery(value: string) {
  searchForm.query = value
  void handleSearch()
}

function startNewConversation() {
  createConversation()
}

function useQuickPrompt(prompt: string) {
  if (!currentConversation.value) {
    createConversation(prompt.slice(0, 16) || '新对话')
  }
  chatForm.input = prompt
}

async function sendChatMessage() {
  const userInput = chatForm.input.trim()
  if (!userInput) {
    ElMessage.warning('请输入聊天内容。')
    return
  }

  const session = ensureConversation()
  if (!session.messages.length) {
    session.title = userInput.slice(0, 18) || '新对话'
  }

  session.messages.push({ role: 'user', content: userInput })
  session.messages.push({ role: 'assistant', content: '' })
  session.updatedAt = Date.now()
  chatForm.input = ''
  chatLoading.value = true

  const assistantMessage = session.messages[session.messages.length - 1]
  const controller = new AbortController()
  chatAbortController.value = controller

  try {
    await streamChat(
      {
        model: chatForm.model.trim() || 'qwen-turbo',
        messages: session.messages.filter((message) => message.content.trim()),
      },
      {
        signal: controller.signal,
        onChunk: (chunk) => {
          assistantMessage.content += chunk
          session.updatedAt = Date.now()
        },
      },
    )
  } catch (error) {
    if (controller.signal.aborted) {
      assistantMessage.content = assistantMessage.content || '已停止本次生成。'
    } else {
      session.messages.pop()
      ElMessage.error(getErrorMessage(error, '对话请求失败，请稍后重试。'))
      console.error(error)
    }
  } finally {
    conversations.value = [...conversations.value].sort((a, b) => b.updatedAt - a.updatedAt)
    chatLoading.value = false
    chatAbortController.value = null
  }
}

function stopChat() {
  chatAbortController.value?.abort()
}

function getMessageDisplayContent(message: ChatMessage, index: number): string {
  return (
    message.content ||
    (chatLoading.value && index === (currentConversation.value?.messages.length ?? 0) - 1
      ? '正在生成中...'
      : '')
  )
}

function renderMarkdown(content: string): string {
  return DOMPurify.sanitize(markdown.render(content))
}

onMounted(async () => {
  createConversation()
  if (!isChatMode.value) {
    await loadKnowledgeBaseOptions()
  }
})

watch(
  isChatMode,
  async (chatMode) => {
    if (!chatMode && !knowledgeBases.value.length) {
      await loadKnowledgeBaseOptions()
    }
  },
  { immediate: false },
)
</script>

<template>
  <div class="page ai-page">
    <section :class="['ai-shell', { 'ai-shell--chat': isChatMode }]">
      <aside class="ai-sidebar">
        <el-button
          v-if="isChatMode"
          class="ai-sidebar__new"
          type="primary"
          :icon="Plus"
          @click="startNewConversation"
        >
          新建对话
        </el-button>

        <div v-if="isChatMode" class="chat-session-list">
          <button
            v-for="session in conversations"
            :key="session.id"
            type="button"
            class="chat-session"
            :class="{ 'chat-session--active': session.id === currentConversationId }"
            @click="currentConversationId = session.id"
          >
            <strong>{{ session.title }}</strong>
            <span>{{ session.messages.length ? `${session.messages.length} 条消息` : '空会话' }}</span>
          </button>
        </div>

        <div v-else class="search-shortcuts">
          <span class="search-shortcuts__label">快捷检索</span>
          <button
            v-for="item in quickQueries"
            :key="item"
            type="button"
            class="search-shortcuts__item"
            @click="applyQuickQuery(item)"
          >
            {{ item }}
          </button>
          <div class="search-shortcuts__footer">
            <strong>{{ knowledgeBases.length }}</strong>
            <span>个知识库可用于筛选</span>
          </div>
        </div>
      </aside>

      <section class="ai-main">
        <header class="ai-main__header">
          <div class="ai-main__title">
            <strong>{{ pageTitle }}</strong>
            <span>{{ pageSubtitle }}</span>
          </div>
          <el-input
            v-if="isChatMode"
            v-model="chatForm.model"
            placeholder="模型，例如 qwen-turbo"
            class="ai-main__model"
          />
        </header>

        <template v-if="isChatMode">
          <div class="ai-main__body chat-body">
            <div v-if="!currentConversation?.messages.length" class="chat-empty">
              <h2>今天想问点什么？</h2>
              <div class="chat-empty__prompts">
                <button
                  v-for="prompt in quickPrompts"
                  :key="prompt"
                  type="button"
                  class="chat-empty__prompt"
                  @click="useQuickPrompt(prompt)"
                >
                  {{ prompt }}
                </button>
              </div>
            </div>

            <div v-else class="chat-message-list">
              <article
                v-for="(message, index) in currentConversation.messages"
                :key="`${message.role}_${index}`"
                class="chat-message"
                :class="`chat-message--${message.role}`"
              >
                <div class="chat-message__role">
                  {{ message.role === 'user' ? '你' : message.role === 'assistant' ? 'AI' : '系统' }}
                </div>
                <div
                  v-if="message.role === 'assistant' || message.role === 'system'"
                  class="chat-message__bubble chat-message__bubble--markdown"
                  v-html="renderMarkdown(getMessageDisplayContent(message, index))"
                />
                <div v-else class="chat-message__bubble">
                  {{ getMessageDisplayContent(message, index) }}
                </div>
              </article>
            </div>
          </div>

          <footer class="chat-compose">
            <div class="chat-compose__box">
              <el-input
                v-model="chatForm.input"
                type="textarea"
                :rows="4"
                resize="none"
                placeholder="给 AI 发送消息"
                @keydown.ctrl.enter.prevent="sendChatMessage"
              />
              <div class="chat-compose__actions">
                <span>Ctrl + Enter 发送</span>
                <div class="chat-compose__buttons">
                  <el-button v-if="chatLoading" @click="stopChat">停止</el-button>
                  <el-button type="primary" :loading="chatLoading" @click="sendChatMessage">
                    发送
                  </el-button>
                </div>
              </div>
            </div>
          </footer>
        </template>

        <template v-else>
          <div class="ai-main__body search-body">
            <div class="search-toolbar">
              <el-select
                v-model="searchForm.knowledgeBaseId"
                clearable
                placeholder="全部知识库"
                class="search-toolbar__field search-toolbar__select"
              >
                <el-option
                  v-for="item in knowledgeBases"
                  :key="item.id"
                  :label="`${item.name} · ${item.department_name}`"
                  :value="item.id"
                />
              </el-select>
              <el-input
                v-model="searchForm.query"
                placeholder="输入关键词"
                class="search-toolbar__field search-toolbar__input"
                @keyup.enter="handleSearch"
              />
              <el-input-number v-model="searchForm.limit" :min="1" :max="20" />
              <el-button type="primary" :loading="loading" @click="handleSearch">
                开始检索
              </el-button>
            </div>

            <div class="quick-query-list">
              <span>推荐：</span>
              <el-button
                v-for="item in quickQueries"
                :key="item"
                text
                @click="applyQuickQuery(item)"
              >
                {{ item }}
              </el-button>
            </div>

            <el-empty
              v-if="!response"
              description="输入关键词后开始检索。"
            />

            <div v-else-if="response.results.length" class="result-stack">
              <article v-for="(item, index) in response.results" :key="index" class="result-card">
                <div class="result-card__meta">
                  <strong>命中片段 {{ index + 1 }}</strong>
                  <el-tag round>score {{ item.score.toFixed(3) }}</el-tag>
                </div>
                <div class="result-card__source">
                  <span v-if="item.metadata.department_name">{{ item.metadata.department_name }}</span>
                  <span v-if="item.metadata.knowledge_base_name">{{ item.metadata.knowledge_base_name }}</span>
                  <span v-if="item.metadata.filename">{{ item.metadata.filename }}</span>
                </div>
                <p>{{ item.content }}</p>
                <small v-if="item.metadata.retrieval_mode">
                  {{ item.metadata.retrieval_mode }}
                </small>
              </article>
            </div>

            <el-empty
              v-else
              description="没有找到结果。"
            />
          </div>
        </template>
      </section>
    </section>
  </div>
</template>

<style scoped>
.ai-page {
  min-height: calc(100vh - 160px);
}

.ai-shell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 18px;
  min-height: calc(100vh - 160px);
}

.ai-shell--chat {
  height: calc(100dvh - 160px);
  min-height: calc(100dvh - 160px);
  overflow: hidden;
}

.ai-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  border-radius: 24px;
  padding: 16px;
  background:
    radial-gradient(circle at top, rgba(240, 198, 112, 0.18), transparent 32%),
    linear-gradient(180deg, #1b6b56 0%, #123e35 58%, #102c27 100%);
  color: #f6f1e8;
}

.ai-sidebar__new {
  width: 100%;
  justify-content: flex-start;
}

.chat-session-list,
.search-shortcuts {
  display: grid;
  gap: 10px;
  min-height: 0;
}

.chat-session-list {
  flex: 1;
  overflow-y: auto;
}

.chat-session {
  display: flex;
  width: 100%;
  flex-direction: column;
  gap: 6px;
  border: 1px solid transparent;
  border-radius: 16px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.04);
  color: #f6f1e8;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.chat-session:hover,
.search-shortcuts__item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.chat-session--active {
  border-color: rgba(255, 248, 232, 0.08);
  background: rgba(255, 248, 232, 0.16);
}

.chat-session strong,
.search-shortcuts__footer strong {
  font-size: 14px;
  font-weight: 600;
}

.chat-session span,
.search-shortcuts__label,
.search-shortcuts__footer span {
  color: rgba(246, 241, 232, 0.76);
  font-size: 12px;
  line-height: 1.5;
}

.search-shortcuts__item {
  border: 0;
  border-radius: 14px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.04);
  color: #f6f1e8;
  text-align: left;
  cursor: pointer;
}

.search-shortcuts__footer {
  margin-top: auto;
  border-top: 1px solid rgba(255, 248, 232, 0.1);
  padding-top: 14px;
}

.ai-main {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background: #ffffff;
  overflow: hidden;
}

.ai-main__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  padding: 18px 24px;
}

.ai-main__title strong {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.ai-main__title span {
  display: block;
  margin-top: 4px;
  color: #6b7280;
  font-size: 13px;
}

.ai-main__model {
  width: 220px;
}

.ai-main__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.chat-body {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-empty {
  display: grid;
  gap: 20px;
  max-width: 760px;
  margin: auto;
  text-align: center;
}

.chat-empty h2 {
  margin: 0;
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 600;
  color: #111827;
}

.chat-empty__prompts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.chat-empty__prompt {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  padding: 14px;
  background: #f7f7f8;
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.chat-message-list {
  display: grid;
  gap: 24px;
  width: min(100%, 880px);
  margin: 0 auto;
  padding: 28px 24px 24px;
}

.chat-message {
  display: grid;
  gap: 8px;
}

.chat-message--user {
  justify-items: end;
}

.chat-message--assistant,
.chat-message--system {
  justify-items: start;
}

.chat-message__role {
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
}

.chat-message__bubble {
  max-width: min(100%, 760px);
  border-radius: 20px;
  padding: 16px 18px;
  background: #f7f7f8;
  color: #111827;
  line-height: 1.8;
  white-space: pre-wrap;
}

.chat-message--user .chat-message__bubble {
  background: #1b6b56;
  color: #fffdf7;
}

.chat-message__bubble--markdown {
  width: min(100%, 760px);
  white-space: normal;
}

.chat-message__bubble--markdown :deep(p),
.chat-message__bubble--markdown :deep(ul),
.chat-message__bubble--markdown :deep(ol),
.chat-message__bubble--markdown :deep(pre),
.chat-message__bubble--markdown :deep(blockquote),
.chat-message__bubble--markdown :deep(table) {
  margin: 0 0 14px;
}

.chat-message__bubble--markdown :deep(p:last-child),
.chat-message__bubble--markdown :deep(ul:last-child),
.chat-message__bubble--markdown :deep(ol:last-child),
.chat-message__bubble--markdown :deep(pre:last-child),
.chat-message__bubble--markdown :deep(blockquote:last-child),
.chat-message__bubble--markdown :deep(table:last-child) {
  margin-bottom: 0;
}

.chat-message__bubble--markdown :deep(ul),
.chat-message__bubble--markdown :deep(ol) {
  padding-left: 20px;
}

.chat-message__bubble--markdown :deep(li + li) {
  margin-top: 6px;
}

.chat-message__bubble--markdown :deep(pre) {
  overflow-x: auto;
  border-radius: 14px;
  padding: 14px;
  background: #111827;
  color: #f9fafb;
}

.chat-message__bubble--markdown :deep(code) {
  border-radius: 6px;
  padding: 2px 6px;
  background: rgba(15, 23, 42, 0.08);
  font-family: 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
  font-size: 0.92em;
}

.chat-message__bubble--markdown :deep(pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
}

.chat-message__bubble--markdown :deep(blockquote) {
  border-left: 3px solid rgba(15, 23, 42, 0.2);
  padding-left: 12px;
  color: #4b5563;
}

.chat-message__bubble--markdown :deep(a) {
  color: #2563eb;
}

.chat-message__bubble--markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.chat-message__bubble--markdown :deep(th),
.chat-message__bubble--markdown :deep(td) {
  border: 1px solid rgba(15, 23, 42, 0.08);
  padding: 8px 10px;
  text-align: left;
}

.chat-compose {
  flex-shrink: 0;
  padding: 0 24px 24px;
}

.chat-compose__box {
  width: min(100%, 880px);
  margin: 0 auto;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  padding: 12px;
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.chat-compose__box :deep(.el-textarea__inner) {
  border: 0;
  box-shadow: none;
  min-height: 96px !important;
}

.chat-compose__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.chat-compose__actions span {
  color: #6b7280;
  font-size: 12px;
}

.chat-compose__buttons {
  display: flex;
  gap: 10px;
}

.search-body {
  display: grid;
  align-content: flex-start;
  gap: 16px;
  padding: 24px;
}

.search-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.search-toolbar__field {
  min-width: 180px;
}

.search-toolbar__select {
  width: 240px;
}

.search-toolbar__input {
  flex: 1 1 280px;
}

.quick-query-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #6b7280;
}

.result-stack {
  display: grid;
  gap: 14px;
}

.result-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 20px;
  padding: 18px;
  background: #ffffff;
}

.result-card__meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.result-card__source {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
  color: #6b7280;
  font-size: 13px;
}

.result-card p {
  margin: 0;
  color: #111827;
  line-height: 1.8;
  white-space: pre-line;
}

.result-card small {
  display: inline-block;
  margin-top: 10px;
  color: #6b7280;
}

@media (max-width: 1080px) {
  .ai-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .ai-main__header,
  .chat-compose__actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .chat-empty__prompts {
    grid-template-columns: 1fr;
  }

  .ai-main__model,
  .search-toolbar__select,
  .search-toolbar__field,
  .chat-compose__buttons {
    width: 100%;
  }
}
</style>
