<script setup lang="ts">
import axios from 'axios'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { streamChat } from '@/api/modules/rag'
import { useAuthStore } from '@/stores/auth'
import { getPreferredMembership } from '@/utils/organization'
import type { ChatMessage } from '@/types/rag'

interface ChatSession {
  id: string
  title: string
  updatedAt: number
  messages: ChatMessage[]
}

const chatForm = ref({
  input: '',
  model: 'qwen-turbo',
})

const quickPrompts = [
  '工作台里都有哪些信息，分别代表什么？',
  '如果我要新建知识空间，应该去哪一步步操作？',
  '结合我当前的部门和权限，帮我说明我能使用哪些模块。',
]

const conversations = ref<ChatSession[]>([])
const currentConversationId = ref('')
const chatLoading = ref(false)
const chatAbortController = ref<AbortController | null>(null)
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const currentMembership = computed(() =>
  getPreferredMembership(authStore.user?.memberships ?? []),
)
const currentConversation = computed(
  () => conversations.value.find((item) => item.id === currentConversationId.value) ?? null,
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

function startNewConversation() {
  createConversation()
}

function useQuickPrompt(prompt: string) {
  const session = ensureConversation()
  if (!session.messages.length) {
    session.title = prompt.slice(0, 18) || '新对话'
  }
  chatForm.value.input = prompt
}

async function sendChatMessage() {
  const userInput = chatForm.value.input.trim()
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
  chatForm.value.input = ''
  chatLoading.value = true

  const assistantMessage = session.messages[session.messages.length - 1]
  const controller = new AbortController()
  chatAbortController.value = controller

  try {
    await streamChat(
      {
        model: chatForm.value.model.trim() || 'qwen-turbo',
        messages: session.messages.filter((message) => message.content.trim()),
        active_department_id: currentMembership.value?.department_id,
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
      const message = getErrorMessage(error, '对话请求失败，请稍后重试。')
      ElMessage.error(message)
      if (message.includes('登录状态已失效')) {
        authStore.logout()
        void router.push({
          name: 'login',
          query: { redirect: route.fullPath },
        })
      }
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

if (!conversations.value.length) {
  createConversation()
}
</script>

<template>
  <div class="chat-page">
    <aside class="chat-page__sidebar">
      <div class="chat-page__sidebar-top">
        <el-button type="primary" :icon="Plus" @click="startNewConversation">
          新建对话
        </el-button>
        <el-input v-model="chatForm.model" placeholder="模型" />
      </div>

      <div class="chat-session-list">
        <button
          v-for="session in conversations"
          :key="session.id"
          type="button"
          :class="['chat-session', { 'chat-session--active': session.id === currentConversationId }]"
          @click="currentConversationId = session.id"
        >
          <strong>{{ session.title }}</strong>
          <span>{{ session.messages.length ? `${session.messages.length} 条消息` : '空会话' }}</span>
        </button>
      </div>
    </aside>

    <section class="chat-page__main">
      <header class="chat-page__header">
        <div>
          <strong>{{ currentConversation?.title || '新对话' }}</strong>
          <span>{{ currentConversation?.messages.length || 0 }} 条消息</span>
        </div>
      </header>

      <div class="chat-page__body">
        <div v-if="!currentConversation?.messages.length" class="chat-empty">
          <div class="chat-empty__title">可以直接问系统怎么用，或者问我当前的数据状态</div>
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
            :class="['chat-message', `chat-message--${message.role}`]"
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
            placeholder="输入消息，Ctrl + Enter 发送"
            @keydown.ctrl.enter.prevent="sendChatMessage"
          />
          <div class="chat-compose__actions">
            <span>已复用当前系统登录状态，并带入系统手册、当前用户、部门和实时业务摘要</span>
            <div class="chat-compose__buttons">
              <el-button v-if="chatLoading" @click="stopChat">停止</el-button>
              <el-button type="primary" :loading="chatLoading" @click="sendChatMessage">
                发送
              </el-button>
            </div>
          </div>
        </div>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.chat-page {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  height: calc(100vh - 88px);
  min-height: calc(100vh - 88px);
  background: #f5f7fa;
}

.chat-page__sidebar {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 16px;
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
  padding: 16px;
}

.chat-page__sidebar-top {
  display: grid;
  gap: 12px;
}

.chat-session-list {
  display: grid;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
}

.chat-session {
  display: grid;
  gap: 4px;
  width: 100%;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  padding: 12px;
  background: #ffffff;
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.chat-session strong {
  font-size: 14px;
  font-weight: 600;
}

.chat-session span {
  color: #6b7280;
  font-size: 12px;
}

.chat-session--active {
  border-color: #409eff;
  background: #ecf5ff;
}

.chat-page__main {
  display: flex;
  min-height: 0;
  flex-direction: column;
}

.chat-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  background: #ffffff;
  padding: 16px 24px;
}

.chat-page__header strong {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.chat-page__header span {
  color: #6b7280;
  font-size: 12px;
}

.chat-page__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.chat-empty {
  display: grid;
  gap: 16px;
  width: min(720px, 100%);
  margin: 72px auto 0;
  padding: 0 24px;
}

.chat-empty__title {
  font-size: 26px;
  font-weight: 600;
  color: #111827;
  text-align: center;
}

.chat-empty__prompts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.chat-empty__prompt {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  padding: 14px;
  background: #ffffff;
  color: #111827;
  text-align: left;
  cursor: pointer;
}

.chat-message-list {
  display: grid;
  gap: 24px;
  width: min(960px, 100%);
  margin: 0 auto;
  padding: 28px 24px;
}

.chat-message {
  display: grid;
  gap: 8px;
}

.chat-message--user {
  justify-items: end;
}

.chat-message__role {
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
}

.chat-message__bubble {
  max-width: min(100%, 820px);
  border-radius: 16px;
  padding: 16px 18px;
  background: #ffffff;
  color: #111827;
  line-height: 1.8;
  white-space: pre-wrap;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.chat-message--user .chat-message__bubble {
  background: #409eff;
  border-color: #409eff;
  color: #ffffff;
}

.chat-message__bubble--markdown {
  width: min(100%, 820px);
  white-space: normal;
}

.chat-message__bubble--markdown :deep(p),
.chat-message__bubble--markdown :deep(ul),
.chat-message__bubble--markdown :deep(ol),
.chat-message__bubble--markdown :deep(pre),
.chat-message__bubble--markdown :deep(blockquote),
.chat-message__bubble--markdown :deep(table) {
  margin: 0 0 12px;
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

.chat-message__bubble--markdown :deep(pre) {
  overflow-x: auto;
  border-radius: 10px;
  padding: 14px;
  background: #111827;
  color: #f9fafb;
}

.chat-message__bubble--markdown :deep(code) {
  border-radius: 6px;
  padding: 2px 5px;
  background: rgba(15, 23, 42, 0.08);
  font-family: 'Cascadia Code', Consolas, monospace;
}

.chat-message__bubble--markdown :deep(pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
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
  padding: 16px 24px 24px;
}

.chat-compose__box {
  width: min(960px, 100%);
  margin: 0 auto;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  padding: 12px;
  background: #ffffff;
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

@media (max-width: 1080px) {
  .chat-page {
    grid-template-columns: 1fr;
    height: auto;
    min-height: calc(100vh - 88px);
  }

  .chat-page__sidebar {
    border-right: 0;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  }

  .chat-empty__prompts {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .chat-compose__actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .chat-compose__buttons {
    width: 100%;
  }
}
</style>
