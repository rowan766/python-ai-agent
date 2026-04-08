<script setup lang="ts">
import type { AxiosError } from 'axios'
import { Delete, Download, UploadFilled } from '@element-plus/icons-vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteKnowledgeDocument,
  downloadKnowledgeDocument,
  fetchKnowledgeBases,
  fetchKnowledgeDocuments,
} from '@/api/modules/knowledge'
import { useAuthStore } from '@/stores/auth'
import type { KnowledgeBaseItem, KnowledgeDocumentItem } from '@/types/knowledge'
import { formatVisibilityScope, getPreferredMembership } from '@/utils/organization'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const downloadingDocumentId = ref<number | null>(null)
const deletingDocumentId = ref<number | null>(null)
const knowledgeBases = ref<KnowledgeBaseItem[]>([])
const documents = ref<KnowledgeDocumentItem[]>([])
const memberships = computed(() => authStore.user?.memberships ?? [])
const preferredMembership = computed(() => getPreferredMembership(memberships.value))
const selectedKnowledgeBaseId = ref<number | undefined>(undefined)
const selectedDepartmentId = ref<number | undefined>(preferredMembership.value?.department_id)
const downloadableCount = computed(() =>
  documents.value.filter((item) => item.download_available).length,
)
const deletableCount = computed(() => documents.value.filter((item) => item.can_delete).length)

function syncFromRoute() {
  const rawKnowledgeBaseId = route.query.knowledgeBaseId
  if (typeof rawKnowledgeBaseId === 'string' && rawKnowledgeBaseId.trim()) {
    const parsed = Number(rawKnowledgeBaseId)
    selectedKnowledgeBaseId.value = Number.isInteger(parsed) ? parsed : undefined
  }
}

async function loadDocuments() {
  loading.value = true
  try {
    const [knowledgeBaseResult, documentResult] = await Promise.all([
      fetchKnowledgeBases(),
      fetchKnowledgeDocuments({
        knowledge_base_id: selectedKnowledgeBaseId.value,
        department_id: selectedDepartmentId.value,
      }),
    ])
    knowledgeBases.value = knowledgeBaseResult.items
    documents.value = documentResult.items
  } catch (error) {
    ElMessage.error('读取文档中心数据失败，请稍后重试。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

function openUpload() {
  void router.push({
    name: 'document-upload',
    query: selectedKnowledgeBaseId.value
      ? { knowledgeBaseId: String(selectedKnowledgeBaseId.value) }
      : undefined,
  })
}

async function handleDownload(document: KnowledgeDocumentItem) {
  downloadingDocumentId.value = document.id
  try {
    await downloadKnowledgeDocument(document.id, document.filename)
    ElMessage.success(`已开始下载 ${document.filename}`)
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '下载文档失败，请稍后重试。')
    console.error(error)
  } finally {
    downloadingDocumentId.value = null
  }
}

async function handleDelete(document: KnowledgeDocumentItem) {
  try {
    await ElMessageBox.confirm(
      `删除后将移除《${document.title}》的源文件和全部检索切片，确认继续吗？`,
      '删除文档',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  deletingDocumentId.value = document.id
  try {
    const result = await deleteKnowledgeDocument(document.id)
    ElMessage.success(result.message)
    await loadDocuments()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '删除文档失败，请稍后重试。')
    console.error(error)
  } finally {
    deletingDocumentId.value = null
  }
}

watch(
  preferredMembership,
  (membership) => {
    if (!selectedDepartmentId.value && membership) {
      selectedDepartmentId.value = membership.department_id
    }
  },
  { immediate: true },
)

watch(
  () => route.query.knowledgeBaseId,
  () => {
    syncFromRoute()
    void loadDocuments()
  },
)

watch(
  [selectedKnowledgeBaseId, selectedDepartmentId],
  () => {
    void loadDocuments()
  },
  { immediate: true },
)

syncFromRoute()
</script>

<template>
  <div class="page">
    <section class="page-toolbar">
      <div class="page-toolbar__title">
        <h2>文档中心</h2>
        <span>当前部门：{{ preferredMembership?.department_name || '未设置' }}</span>
      </div>
      <div class="page-toolbar__actions">
        <el-button @click="router.push('/knowledge-bases')">知识空间</el-button>
        <el-button type="primary" :icon="UploadFilled" @click="openUpload">上传文档</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">当前列表文档</span>
        <strong class="summary-card__value">{{ documents.length }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">可下载文档</span>
        <strong class="summary-card__value">{{ downloadableCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">可删除文档</span>
        <strong class="summary-card__value">{{ deletableCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">当前知识空间</span>
        <strong class="summary-card__value">
          {{
            knowledgeBases.find((item) => item.id === selectedKnowledgeBaseId)?.name
            || '全部空间'
          }}
        </strong>
      </el-card>
    </section>

    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-toolbar">
          <strong>文档清单</strong>
          <div class="table-toolbar__filters">
            <el-select
              v-model="selectedDepartmentId"
              clearable
              placeholder="按部门筛选"
              class="toolbar-select"
            >
              <el-option
                v-for="membership in memberships"
                :key="membership.department_id"
                :label="membership.department_name"
                :value="membership.department_id"
              />
            </el-select>
            <el-select
              v-model="selectedKnowledgeBaseId"
              clearable
              placeholder="按知识空间筛选"
              class="toolbar-select"
            >
              <el-option
                v-for="item in knowledgeBases"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="documents" stripe empty-text="当前没有文档">
        <el-table-column prop="title" label="文档标题" min-width="220" />
        <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="knowledge_base_name" label="知识空间" min-width="180" />
        <el-table-column prop="department_name" label="归属部门" min-width="140" />
        <el-table-column prop="uploader_username" label="上传人" min-width="120" />
        <el-table-column prop="chunks_count" label="切片数" width="100" />
        <el-table-column label="可见范围" min-width="150">
          <template #default="{ row }">
            {{ formatVisibilityScope(row.visibility_scope) }}
          </template>
        </el-table-column>
        <el-table-column prop="file_extension" label="格式" width="100" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              text
              :icon="Download"
              :disabled="!row.download_available"
              :loading="downloadingDocumentId === row.id"
              @click="handleDownload(row)"
            >
              下载
            </el-button>
            <el-button
              type="danger"
              text
              :icon="Delete"
              :disabled="!row.can_delete"
              :loading="deletingDocumentId === row.id"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar-select {
  width: 220px;
}

@media (max-width: 960px) {
  .toolbar-select {
    width: 100%;
  }
}
</style>
