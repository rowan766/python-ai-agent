<script setup lang="ts">
import type { AxiosError } from 'axios'
import { Delete, Download, UploadFilled } from '@element-plus/icons-vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  deleteKnowledgeDocument,
  downloadKnowledgeDocument,
  fetchKnowledgeBases,
  fetchKnowledgeDocuments,
} from '@/api/modules/knowledge'
import { useAuthStore } from '@/stores/auth'
import type { KnowledgeBaseItem, KnowledgeDocumentItem } from '@/types/knowledge'
import { ElMessage, ElMessageBox } from 'element-plus'
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
const downloadableCount = computed(() => documents.value.filter((item) => item.download_available).length)
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
    query: selectedKnowledgeBaseId.value ? { knowledgeBaseId: String(selectedKnowledgeBaseId.value) } : undefined,
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

watch([selectedKnowledgeBaseId, selectedDepartmentId], () => {
  void loadDocuments()
}, { immediate: true })

syncFromRoute()
</script>

<template>
  <div class="page">
    <section class="hero-card document-hero">
      <div>
        <p class="page-eyebrow">Documents</p>
        <h2>文档页只负责浏览、下载和清理，不再把空间创建和上传塞进同一页。</h2>
        <p class="page-copy">
          先筛到当前工作部门或指定空间，再处理文档清单。上传动作已经独立到单独页面，减少理解成本。
        </p>
      </div>
      <div class="document-hero__actions">
        <el-button plain @click="router.push('/knowledge-bases')">返回知识空间</el-button>
        <el-button type="primary" :icon="UploadFilled" @click="openUpload">上传文档</el-button>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">当前列表文档</span>
        <strong>{{ documents.length }}</strong>
        <p>已按当前筛选范围收敛到和你操作有关的文档。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可下载文档</span>
        <strong>{{ downloadableCount }}</strong>
        <p>具备原始文件下载能力的文档数量。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可删除文档</span>
        <strong>{{ deletableCount }}</strong>
        <p>当前账号有权限清理的文档数量。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">默认工作部门</span>
        <strong>{{ preferredMembership?.department_name || '--' }}</strong>
        <p>顶部切换工作部门后，这里的默认筛选也会随之变化。</p>
      </el-card>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>
        <div class="table-header">
          <strong>文档清单</strong>
          <div class="table-header__actions">
            <el-select
              v-model="selectedDepartmentId"
              clearable
              placeholder="按部门筛选"
              class="table-header__select"
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
              class="table-header__select"
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

      <el-table v-loading="loading" :data="documents" stripe>
        <el-table-column prop="title" label="文档标题" min-width="220" />
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

      <el-empty
        v-if="!loading && !documents.length"
        description="当前筛选范围内还没有文档。你可以先进入上传页，把资料投递到某个知识空间。"
      />
    </el-card>
  </div>
</template>

<style scoped>
.document-hero {
  align-items: center;
}

.document-hero__actions,
.table-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.table-header strong {
  color: var(--page-green-deep);
}

.table-header__select {
  width: 220px;
}

@media (max-width: 960px) {
  .document-hero,
  .table-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .table-header__select {
    width: 100%;
  }
}
</style>
