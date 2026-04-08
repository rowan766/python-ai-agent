<script setup lang="ts">
import type { AxiosError } from 'axios'
import { UploadFilled } from '@element-plus/icons-vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchKnowledgeBases, uploadKnowledgeDocument } from '@/api/modules/knowledge'
import { fetchSupportedFormats } from '@/api/modules/rag'
import type { KnowledgeBaseItem, UploadKnowledgeDocumentResponse } from '@/types/knowledge'
import type { UploadRequestOptions } from 'element-plus'
import { formatVisibilityScope, getPreferredMembership } from '@/utils/organization'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const uploading = ref(false)
const loading = ref(false)
const supportedFormats = ref<string[]>([])
const knowledgeBases = ref<KnowledgeBaseItem[]>([])
const selectedKnowledgeBaseId = ref<number | undefined>(undefined)
const selectedVisibilityScope = ref('knowledge_base_default')
const uploadResult = ref<UploadKnowledgeDocumentResponse | null>(null)

const memberships = computed(() => authStore.user?.memberships ?? [])
const preferredMembership = computed(() => getPreferredMembership(memberships.value))
const selectedKnowledgeBase = computed(
  () => knowledgeBases.value.find((item) => item.id === selectedKnowledgeBaseId.value) ?? null,
)
const acceptValue = computed(() => supportedFormats.value.join(','))

const visibilityOptions = [
  { label: '沿用空间策略', value: 'knowledge_base_default' },
  { label: '本部门可见', value: 'department_private' },
  { label: '共享后可见', value: 'department_shared' },
  { label: '全组织可见', value: 'org_public' },
]

function syncKnowledgeBaseFromRoute() {
  const rawKnowledgeBaseId = route.query.knowledgeBaseId
  if (typeof rawKnowledgeBaseId !== 'string' || !rawKnowledgeBaseId.trim()) {
    return
  }

  const parsed = Number(rawKnowledgeBaseId)
  if (Number.isInteger(parsed)) {
    selectedKnowledgeBaseId.value = parsed
  }
}

async function loadOptions() {
  loading.value = true
  try {
    const [formatResult, knowledgeBaseResult] = await Promise.all([
      fetchSupportedFormats(),
      fetchKnowledgeBases(),
    ])
    supportedFormats.value = formatResult.supported_formats
    knowledgeBases.value = knowledgeBaseResult.items

    const hasSelectedKnowledgeBase = knowledgeBaseResult.items.some(
      (item) => item.id === selectedKnowledgeBaseId.value,
    )

    if (!hasSelectedKnowledgeBase) {
      const preferredBase =
        knowledgeBaseResult.items.find(
          (item) => item.department_id === preferredMembership.value?.department_id,
        ) ?? knowledgeBaseResult.items[0]
      selectedKnowledgeBaseId.value = preferredBase?.id
    }
  } catch (error) {
    ElMessage.error('读取上传配置失败，请稍后重试。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleUpload(options: UploadRequestOptions) {
  if (!selectedKnowledgeBaseId.value) {
    ElMessage.warning('请先选择归属知识空间。')
    return
  }

  uploading.value = true
  uploadResult.value = null

  try {
    const file = options.file as File
    const result = await uploadKnowledgeDocument({
      file,
      knowledge_base_id: selectedKnowledgeBaseId.value,
      visibility_scope: selectedVisibilityScope.value,
    })
    uploadResult.value = result
    ElMessage.success(`上传成功，已生成 ${result.document.chunks_count} 个片段。`)
    options.onSuccess?.(result)
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(
      axiosError.response?.data?.detail
      || axiosError.message
      || '上传失败，请确认后端服务、模型配置和文件格式。',
    )
    console.error(error)
  } finally {
    uploading.value = false
  }
}

watch(
  () => route.query.knowledgeBaseId,
  () => {
    syncKnowledgeBaseFromRoute()
  },
)

onMounted(async () => {
  syncKnowledgeBaseFromRoute()
  await loadOptions()
})
</script>

<template>
  <div class="page">
    <section class="page-toolbar">
      <div class="page-toolbar__title">
        <h2>上传文档</h2>
        <span>当前部门：{{ preferredMembership?.department_name || '未设置' }}</span>
      </div>
      <div class="page-toolbar__actions">
        <el-button @click="router.push('/knowledge-bases')">知识空间</el-button>
        <el-button @click="router.push('/documents')">文档中心</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">目标空间</span>
        <strong class="summary-card__value">{{ selectedKnowledgeBase?.name || '--' }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">归属部门</span>
        <strong class="summary-card__value">{{ selectedKnowledgeBase?.department_name || '--' }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">可见范围</span>
        <strong class="summary-card__value">{{ formatVisibilityScope(selectedVisibilityScope) }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">支持格式</span>
        <strong class="summary-card__value">{{ supportedFormats.length }}</strong>
      </el-card>
    </section>

    <section class="split-grid">
      <el-card class="form-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>上传表单</strong>
          </div>
        </template>

        <el-alert
          v-if="!knowledgeBases.length"
          class="upload-alert"
          title="当前没有可上传的知识空间"
          type="warning"
          :closable="false"
          show-icon
        />

        <el-form label-position="top">
          <el-form-item label="归属知识空间">
            <el-select
              v-model="selectedKnowledgeBaseId"
              :loading="loading"
              placeholder="请选择知识空间"
              style="width: 100%"
            >
              <el-option
                v-for="item in knowledgeBases"
                :key="item.id"
                :label="`${item.name} · ${item.department_name}`"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="文档可见范围">
            <el-radio-group v-model="selectedVisibilityScope">
              <el-radio-button
                v-for="option in visibilityOptions"
                :key="option.value"
                :label="option.value"
              >
                {{ option.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <el-upload
          drag
          :accept="acceptValue"
          :show-file-list="false"
          :http-request="handleUpload"
          :disabled="uploading || !knowledgeBases.length"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件到这里，或 <em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">
              {{ supportedFormats.join(' / ') || '正在读取格式配置...' }}
            </div>
          </template>
        </el-upload>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>目标确认</strong>
          </div>
        </template>

        <div class="compact-stack">
          <div class="compact-row">
            <span>空间名称</span>
            <strong>{{ selectedKnowledgeBase?.name || '--' }}</strong>
          </div>
          <div class="compact-row">
            <span>归属部门</span>
            <strong>{{ selectedKnowledgeBase?.department_name || '--' }}</strong>
          </div>
          <div class="compact-row">
            <span>空间默认范围</span>
            <strong>
              {{
                selectedKnowledgeBase
                  ? formatVisibilityScope(selectedKnowledgeBase.visibility_scope)
                  : '--'
              }}
            </strong>
          </div>
          <div class="compact-row">
            <span>已有文档</span>
            <strong>{{ selectedKnowledgeBase?.document_count ?? 0 }}</strong>
          </div>
        </div>
      </el-card>
    </section>

    <el-card v-if="uploadResult" class="table-card" shadow="never">
      <template #header>
        <div class="table-toolbar">
          <strong>最近一次上传结果</strong>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="状态">{{ uploadResult.status }}</el-descriptions-item>
        <el-descriptions-item label="文件名">{{ uploadResult.document.filename }}</el-descriptions-item>
        <el-descriptions-item label="知识空间">{{ uploadResult.document.knowledge_base_name }}</el-descriptions-item>
        <el-descriptions-item label="归属部门">{{ uploadResult.document.department_name }}</el-descriptions-item>
        <el-descriptions-item label="切片数量">{{ uploadResult.document.chunks_count }}</el-descriptions-item>
        <el-descriptions-item label="可见范围">
          {{ formatVisibilityScope(uploadResult.document.visibility_scope) }}
        </el-descriptions-item>
        <el-descriptions-item label="返回消息">{{ uploadResult.message }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.upload-alert {
  margin-bottom: 16px;
}

.el-upload__tip {
  margin-top: 12px;
  color: #6b7280;
}
</style>
