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
        <p class="page-eyebrow">Enterprise Workspace</p>
        <h2>工作台开始展示真实的知识资产状态，而不只是联调占位页。</h2>
        <p class="page-copy">
          现在这里会汇总你当前能访问的知识库空间、文档规模和模型健康状态。后续审批、共享和知识问答也会继续沿着这条主链扩展。
        </p>
      </div>

      <div class="hero-card__summary">
        <span>{{ authStore.displayName }}</span>
        <small>{{ authStore.user?.email }}</small>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">当前组织状态</span>
        <strong>{{ authStore.organizationReady ? '已加入组织' : '待加入组织' }}</strong>
        <p>完成组织接入后，知识空间和文档权限范围才会正式进入可见区。</p>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可访问知识库</span>
        <strong>{{ knowledgeSummary?.count ?? '--' }}</strong>
        <p>当前登录用户在其组织归属和管理范围内可见的知识空间数量。</p>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可访问文档</span>
        <strong>{{ documentSummary?.count ?? '--' }}</strong>
        <p>这些文档已经有明确的知识库归属，可继续扩展审批与共享策略。</p>
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
          <router-link class="action-tile" to="/documents/upload">
            <strong>上传文档</strong>
            <span>走归属型上传接口，把文档落到指定知识库空间后再进入向量库。</span>
          </router-link>
          <router-link class="action-tile" to="/rag/search">
            <strong>智能检索</strong>
            <span>按当前用户可访问的知识范围检索，观察命中来源和召回方式。</span>
          </router-link>
          <router-link class="action-tile" to="/knowledge-bases">
            <strong>知识库空间</strong>
            <span>查看真实的空间清单，并为部门创建新的知识空间。</span>
          </router-link>
          <router-link class="action-tile" to="/approvals">
            <strong>审批中心</strong>
            <span>当前可处理组织接入申请，后续会继续承接更多治理审批。</span>
          </router-link>
        </div>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>系统联调状态</template>
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
              <p class="muted">
                这一版工作台已经不只是 IA，而是把组织、知识空间、文档归属和权限过滤检索逐步接成真实后台。
              </p>
            </div>
          </template>
        </el-skeleton>
      </el-card>
    </section>
  </div>
</template>
