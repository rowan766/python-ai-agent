<script setup lang="ts">
import { fetchKnowledgeBases, fetchKnowledgeDocuments } from '@/api/modules/knowledge'
import { fetchChatHealth, fetchEmbeddingHealth, fetchSupportedFormats } from '@/api/modules/rag'
import { useAuthStore } from '@/stores/auth'
import type { KnowledgeBaseListResponse, KnowledgeDocumentListResponse } from '@/types/knowledge'
import type { ModelHealthResponse } from '@/types/rag'
import { onMounted, ref } from 'vue'

const authStore = useAuthStore()

const supportedFormats = ref<string[]>([])
const embeddingHealth = ref<ModelHealthResponse | null>(null)
const chatHealth = ref<ModelHealthResponse | null>(null)
const knowledgeSummary = ref<KnowledgeBaseListResponse | null>(null)
const documentSummary = ref<KnowledgeDocumentListResponse | null>(null)
const loading = ref(false)

async function loadDashboard() {
  loading.value = true
  try {
    const [formatsResult, embeddingResult, chatResult, knowledgeResult, documentResult] =
      await Promise.allSettled([
      fetchSupportedFormats(),
      fetchEmbeddingHealth(),
      fetchChatHealth(),
      fetchKnowledgeBases(),
      fetchKnowledgeDocuments(),
    ])

    supportedFormats.value =
      formatsResult.status === 'fulfilled' ? formatsResult.value.supported_formats : []
    embeddingHealth.value = embeddingResult.status === 'fulfilled' ? embeddingResult.value : null
    chatHealth.value = chatResult.status === 'fulfilled' ? chatResult.value : null
    knowledgeSummary.value = knowledgeResult.status === 'fulfilled' ? knowledgeResult.value : null
    documentSummary.value = documentResult.status === 'fulfilled' ? documentResult.value : null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadDashboard()
})
</script>

<template>
  <div class="page">
    <section class="hero-card">
      <div>
        <h2>工作台</h2>
        <p class="page-copy">{{ authStore.user?.email }}</p>
      </div>

      <div class="hero-card__summary">
        <span>{{ authStore.displayName }}</span>
        <small>{{ authStore.organizationReady ? '组织已接入' : '组织待接入' }}</small>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">当前组织状态</span>
        <strong>{{ authStore.organizationReady ? '已加入组织' : '待加入组织' }}</strong>
        <p>组织关系决定权限范围。</p>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可访问知识库</span>
        <strong>{{ knowledgeSummary?.count ?? '--' }}</strong>
        <p>当前账号可见空间。</p>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可访问文档</span>
        <strong>{{ documentSummary?.count ?? '--' }}</strong>
        <p>已入库文档数量。</p>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">支持上传格式</span>
        <strong>{{ supportedFormats.length || '--' }}</strong>
        <p>{{ supportedFormats.join(' / ') || '正在加载格式配置...' }}</p>
      </el-card>
    </section>

    <section class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>快捷入口</template>
        <div class="action-grid">
          <router-link class="action-tile" to="/rag/search">
            <strong>智能问答</strong>
            <span>知识检索与 AI 对话。</span>
          </router-link>
          <router-link class="action-tile" to="/documents?tab=documents">
            <strong>文档中心</strong>
            <span>知识库、文档上传与维护。</span>
          </router-link>
          <router-link class="action-tile" to="/documents?tab=upload">
            <strong>上传新文档</strong>
            <span>上传并写入向量库。</span>
          </router-link>
          <router-link class="action-tile" to="/organization?tab=approvals">
            <strong>组织中心</strong>
            <span>组织、部门、权限与审批。</span>
          </router-link>
        </div>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>系统状态</template>
        <el-skeleton :loading="loading" animated :rows="5">
          <template #default>
            <div class="health-stack">
              <div class="health-row">
                <span>Embedding Health</span>
                <el-tag :type="embeddingHealth?.status === 'ok' ? 'success' : 'danger'">
                  {{ embeddingHealth?.status || 'unknown' }}
                </el-tag>
              </div>
              <div class="health-row">
                <span>Chat Health</span>
                <el-tag :type="chatHealth?.status === 'ok' ? 'success' : 'danger'">
                  {{ chatHealth?.status || 'unknown' }}
                </el-tag>
              </div>
              <div class="health-row">
                <span>Knowledge Spaces</span>
                <el-tag type="success">{{ knowledgeSummary?.count ?? 0 }} 个空间</el-tag>
              </div>
              <div class="health-row">
                <span>API Docs</span>
                <el-tag type="success">/docs 已接入 Scalar</el-tag>
              </div>
            </div>
          </template>
        </el-skeleton>
      </el-card>
    </section>
  </div>
</template>
