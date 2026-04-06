<script setup lang="ts">
import type { AxiosError } from 'axios'
import axios from 'axios'
import { Delete, Download, Plus, UploadFilled } from '@element-plus/icons-vue'
import {
  createKnowledgeBase,
  createKnowledgeBaseShareRequest,
  deleteKnowledgeDocument,
  downloadKnowledgeDocument,
  fetchKnowledgeBaseShares,
  fetchKnowledgeBases,
  fetchKnowledgeDocuments,
  uploadKnowledgeDocument,
} from '@/api/modules/knowledge'
import { fetchDepartmentTree } from '@/api/modules/organization'
import { fetchSupportedFormats } from '@/api/modules/rag'
import { useAuthStore } from '@/stores/auth'
import type { DepartmentNode } from '@/types/organization'
import type {
  CreateKnowledgeBasePayload,
  KnowledgeBaseItem,
  KnowledgeBaseShareItem,
  KnowledgeDocumentItem,
  UploadKnowledgeDocumentResponse,
} from '@/types/knowledge'
import type { UploadRequestOptions } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

type DocumentCenterTab = 'documents' | 'bases' | 'upload'

const VALID_TABS: DocumentCenterTab[] = ['documents', 'bases', 'upload']

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const uploading = ref(false)
const creatingKnowledgeBase = ref(false)
const creatingShareRequest = ref(false)
const downloadingDocumentId = ref<number | null>(null)
const deletingDocumentId = ref<number | null>(null)

const supportedFormats = ref<string[]>([])
const knowledgeBases = ref<KnowledgeBaseItem[]>([])
const documents = ref<KnowledgeDocumentItem[]>([])
const departmentTree = ref<DepartmentNode[]>([])
const shareMap = ref<Record<number, KnowledgeBaseShareItem[]>>({})
const selectedKnowledgeBaseForShare = ref<KnowledgeBaseItem | null>(null)
const uploadResult = ref<UploadKnowledgeDocumentResponse | null>(null)

const documentFilterKnowledgeBaseId = ref<number | undefined>(undefined)
const uploadKnowledgeBaseId = ref<number | undefined>(undefined)
const uploadVisibilityScope = ref('knowledge_base_default')
const createDialogVisible = ref(false)
const shareDialogVisible = ref(false)
const activeTab = ref<DocumentCenterTab>(normalizeTab(route.query.tab))

const createForm = reactive<CreateKnowledgeBasePayload>({
  department_id: 0,
  code: '',
  name: '',
  description: '',
  visibility_scope: 'department_private',
})

const shareForm = reactive({
  target_department_id: undefined as number | undefined,
  reason: '',
})

const visibilityOptions = [
  { label: '沿用知识库默认策略', value: 'knowledge_base_default' },
  { label: '部门私有', value: 'department_private' },
  { label: '部门共享', value: 'department_shared' },
  { label: '全组织公开', value: 'org_public' },
]

const knowledgeBaseVisibilityOptions = [
  { label: '部门私有', value: 'department_private' },
  { label: '部门共享', value: 'department_shared' },
  { label: '全组织公开', value: 'org_public' },
]

const membershipOptions = computed(() => authStore.user?.memberships ?? [])
const primaryMembership = computed(
  () => membershipOptions.value.find((item) => item.is_primary) ?? membershipOptions.value[0],
)
const acceptValue = computed(() => supportedFormats.value.join(','))
const totalChunks = computed(() =>
  documents.value.reduce((total, item) => total + item.chunks_count, 0),
)

function normalizeTab(rawValue: unknown): DocumentCenterTab {
  return VALID_TABS.includes(rawValue as DocumentCenterTab)
    ? (rawValue as DocumentCenterTab)
    : 'documents'
}

function syncTabQuery(tab: DocumentCenterTab) {
  if (route.query.tab === tab) {
    return
  }
  void router.replace({
    name: 'documents',
    query: {
      ...route.query,
      tab,
    },
  })
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  }
  return fallback
}

async function loadData() {
  loading.value = true
  try {
    const [formatResult, knowledgeBaseResult, documentResult, departmentTreeResult] =
      await Promise.all([
        fetchSupportedFormats(),
        fetchKnowledgeBases(),
        fetchKnowledgeDocuments(
          documentFilterKnowledgeBaseId.value
            ? { knowledge_base_id: documentFilterKnowledgeBaseId.value }
            : undefined,
        ),
        fetchDepartmentTree(),
      ])

    supportedFormats.value = formatResult.supported_formats
    knowledgeBases.value = knowledgeBaseResult.items
    documents.value = documentResult.items
    departmentTree.value = departmentTreeResult.items
    uploadKnowledgeBaseId.value = uploadKnowledgeBaseId.value ?? knowledgeBaseResult.items[0]?.id

    const shareEntries = await Promise.all(
      knowledgeBaseResult.items.map(async (item) => {
        try {
          const result = await fetchKnowledgeBaseShares(item.id)
          return [item.id, result.items] as const
        } catch {
          return [item.id, []] as const
        }
      }),
    )
    shareMap.value = Object.fromEntries(shareEntries)

    if (!createForm.department_id && primaryMembership.value) {
      createForm.department_id = primaryMembership.value.department_id
    }
  } catch (error) {
    ElMessage.error('读取文档中心数据失败，请稍后重试。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  if (primaryMembership.value && !createForm.department_id) {
    createForm.department_id = primaryMembership.value.department_id
  }
  createDialogVisible.value = true
}

function openShareDialog(item: KnowledgeBaseItem) {
  selectedKnowledgeBaseForShare.value = item
  shareForm.target_department_id = undefined
  shareForm.reason = ''
  shareDialogVisible.value = true
}

function jumpToUpload(item?: KnowledgeBaseItem) {
  if (item) {
    uploadKnowledgeBaseId.value = item.id
  }
  activeTab.value = 'upload'
}

async function handleCreateKnowledgeBase() {
  if (!createForm.department_id) {
    ElMessage.warning('请先选择归属部门。')
    return
  }
  if (!createForm.name.trim() || !createForm.code.trim()) {
    ElMessage.warning('请补全知识库名称和编码。')
    return
  }

  creatingKnowledgeBase.value = true
  try {
    await createKnowledgeBase({
      ...createForm,
      name: createForm.name.trim(),
      code: createForm.code.trim(),
      description: createForm.description?.trim() || '',
    })
    ElMessage.success('知识库空间创建成功。')
    createDialogVisible.value = false
    createForm.code = ''
    createForm.name = ''
    createForm.description = ''
    createForm.visibility_scope = 'department_private'
    await loadData()
    activeTab.value = 'bases'
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '创建知识库空间失败。')
    console.error(error)
  } finally {
    creatingKnowledgeBase.value = false
  }
}

async function handleCreateShareRequest() {
  if (!selectedKnowledgeBaseForShare.value) {
    return
  }
  if (!shareForm.target_department_id || !shareForm.reason.trim()) {
    ElMessage.warning('请补全目标部门和共享理由。')
    return
  }

  creatingShareRequest.value = true
  try {
    await createKnowledgeBaseShareRequest(selectedKnowledgeBaseForShare.value.id, {
      target_department_id: shareForm.target_department_id,
      reason: shareForm.reason.trim(),
    })
    ElMessage.success('知识库共享申请已提交。')
    shareDialogVisible.value = false
    await loadData()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '提交共享申请失败。')
    console.error(error)
  } finally {
    creatingShareRequest.value = false
  }
}

async function handleUpload(options: UploadRequestOptions) {
  if (!uploadKnowledgeBaseId.value) {
    ElMessage.warning('请先选择归属知识库空间。')
    return
  }

  uploading.value = true
  uploadResult.value = null
  try {
    const file = options.file as File
    const result = await uploadKnowledgeDocument({
      file,
      knowledge_base_id: uploadKnowledgeBaseId.value,
      visibility_scope: uploadVisibilityScope.value,
    })
    uploadResult.value = result
    options.onSuccess?.(result)
    ElMessage.success(`上传成功，已生成 ${result.document.chunks_count} 个切片。`)
    documentFilterKnowledgeBaseId.value = result.document.knowledge_base_id
    await loadData()
    activeTab.value = 'documents'
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '上传失败，请确认后端服务和文件格式。'))
    console.error(error)
  } finally {
    uploading.value = false
  }
}

async function handleDownload(document: KnowledgeDocumentItem) {
  downloadingDocumentId.value = document.id
  try {
    await downloadKnowledgeDocument(document.id, document.filename)
    ElMessage.success(`已开始下载 ${document.filename}`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '下载文档失败，请稍后重试。'))
    console.error(error)
  } finally {
    downloadingDocumentId.value = null
  }
}

async function handleDelete(document: KnowledgeDocumentItem) {
  try {
    await ElMessageBox.confirm(
      `删除后将移除《${document.title}》的原始文件和全部向量切片，确认继续吗？`,
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
    await loadData()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '删除文档失败，请稍后重试。'))
    console.error(error)
  } finally {
    deletingDocumentId.value = null
  }
}

watch(
  () => route.query.tab,
  (value) => {
    activeTab.value = normalizeTab(value)
  },
)

watch(activeTab, (value) => {
  syncTabQuery(value)
})

watch(documentFilterKnowledgeBaseId, async () => {
  await loadData()
})

onMounted(async () => {
  await loadData()
})
</script>

<template>
  <div class="page">
    <section class="hero-card document-hero">
      <div>
        <h2>文档中心</h2>
        <p class="page-copy">知识库空间、文档上传、下载、删除</p>
      </div>
      <div class="document-hero__actions">
        <el-button type="primary" :icon="Plus" :disabled="!membershipOptions.length" @click="openCreateDialog">
          新增知识库空间
        </el-button>
        <el-button :icon="UploadFilled" @click="jumpToUpload()">上传文档</el-button>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">知识库空间</span>
        <strong>{{ knowledgeBases.length }}</strong>
        <p>当前可访问空间。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可见文档</span>
        <strong>{{ documents.length }}</strong>
        <p>当前列表可维护文档。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">入库切片</span>
        <strong>{{ totalChunks }}</strong>
        <p>向量切片总数。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">支持格式</span>
        <strong>{{ supportedFormats.length }}</strong>
        <p>{{ supportedFormats.join(' / ') || '正在读取格式配置...' }}</p>
      </el-card>
    </section>

    <el-card shadow="never" class="soft-card center-tabs">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="文档清单" name="documents">
          <div class="table-header">
            <strong>文档维护</strong>
            <div class="table-header__actions">
              <el-select
                v-model="documentFilterKnowledgeBaseId"
                clearable
                placeholder="按知识库筛选"
                style="width: 220px"
              >
                <el-option
                  v-for="item in knowledgeBases"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
              <el-button :icon="UploadFilled" @click="jumpToUpload()">继续上传</el-button>
            </div>
          </div>

          <el-table v-loading="loading" :data="documents" stripe>
            <el-table-column prop="title" label="文档标题" min-width="220" />
            <el-table-column prop="knowledge_base_name" label="知识库空间" min-width="180" />
            <el-table-column prop="department_name" label="归属部门" min-width="140" />
            <el-table-column prop="uploader_username" label="上传人" min-width="120" />
            <el-table-column prop="chunks_count" label="切片数" width="100" />
            <el-table-column prop="visibility_scope" label="可见性" min-width="150" />
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
            description="当前范围内还没有文档。可以先去上传区向某个知识库空间投递资料。"
          />
        </el-tab-pane>

        <el-tab-pane label="知识库空间" name="bases">
          <div class="section-head">
            <strong>空间管理</strong>
            <el-button type="primary" :icon="Plus" :disabled="!membershipOptions.length" @click="openCreateDialog">
              新增知识库空间
            </el-button>
          </div>

          <el-empty
            v-if="!loading && !knowledgeBases.length"
            description="当前还没有可访问的知识库空间。若你是部门负责人，可先创建首个空间。"
          />

          <div v-else class="kb-grid">
            <article v-for="item in knowledgeBases" :key="item.id" class="kb-card">
              <div class="kb-card__top">
                <div>
                  <strong>{{ item.name }}</strong>
                  <p>{{ item.description || '未填写描述' }}</p>
                </div>
                <el-tag round>{{ item.visibility_scope }}</el-tag>
              </div>

              <div class="kb-card__meta">
                <span>归属部门：{{ item.department_name }}</span>
                <span>编码：{{ item.code }}</span>
                <span>文档数：{{ item.document_count }}</span>
              </div>

              <div class="kb-card__actions">
                <el-button type="primary" plain @click="jumpToUpload(item)">上传到该空间</el-button>
                <el-button plain @click="documentFilterKnowledgeBaseId = item.id; activeTab = 'documents'">
                  查看文档
                </el-button>
                <el-button link type="primary" @click="openShareDialog(item)">发起共享</el-button>
              </div>

              <div class="kb-card__share">
                <div class="kb-card__share-head">
                  <span>已共享给：</span>
                </div>
                <div v-if="shareMap[item.id]?.length" class="kb-card__share-tags">
                  <el-tag
                    v-for="share in shareMap[item.id]"
                    :key="share.id"
                    round
                    type="success"
                  >
                    {{ share.target_department_name }}
                  </el-tag>
                </div>
                <span v-else class="kb-card__share-empty">当前还没有生效的共享目标部门。</span>
              </div>
            </article>
          </div>
        </el-tab-pane>

        <el-tab-pane label="上传文档" name="upload">
          <div class="grid-two">
            <el-card shadow="never" class="soft-card soft-card--inner">
              <template #header>上传入口</template>
              <el-alert
                v-if="!knowledgeBases.length"
                class="upload-alert"
                title="当前还没有可上传的知识库空间。请先创建知识库空间，或联系负责人完成组织接入。"
                type="warning"
                :closable="false"
                show-icon
              />
              <el-form label-position="top" class="upload-form">
                <el-form-item label="归属知识库空间">
                  <el-select
                    v-model="uploadKnowledgeBaseId"
                    placeholder="请选择知识库空间"
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

                <el-form-item label="文档可见性">
                  <el-radio-group v-model="uploadVisibilityScope">
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
                <div class="el-upload__text">
                  拖拽文件到这里，或 <em>点击上传</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">
                    当前支持：{{ supportedFormats.join(' / ') || '正在读取格式配置...' }}
                  </div>
                </template>
              </el-upload>
            </el-card>

            <el-card shadow="never" class="soft-card soft-card--inner">
              <template #header>当前状态</template>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="知识库空间">{{ knowledgeBases.length }}</el-descriptions-item>
                <el-descriptions-item label="文档">{{ documents.length }}</el-descriptions-item>
                <el-descriptions-item label="切片">{{ totalChunks }}</el-descriptions-item>
                <el-descriptions-item label="支持格式">
                  {{ supportedFormats.join(' / ') || '-' }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </div>

          <el-card v-if="uploadResult" shadow="never" class="soft-card upload-result">
            <template #header>最近一次上传结果</template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="状态">{{ uploadResult.status }}</el-descriptions-item>
              <el-descriptions-item label="文件名">{{ uploadResult.document.filename }}</el-descriptions-item>
              <el-descriptions-item label="知识库">{{ uploadResult.document.knowledge_base_name }}</el-descriptions-item>
              <el-descriptions-item label="归属部门">{{ uploadResult.document.department_name }}</el-descriptions-item>
              <el-descriptions-item label="切片数量">{{ uploadResult.document.chunks_count }}</el-descriptions-item>
              <el-descriptions-item label="可见性">{{ uploadResult.document.visibility_scope }}</el-descriptions-item>
              <el-descriptions-item label="返回消息">{{ uploadResult.message }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="新增知识库空间" width="520px">
      <el-form label-position="top">
        <el-form-item label="归属部门">
          <el-select v-model="createForm.department_id" placeholder="请选择归属部门" style="width: 100%">
            <el-option
              v-for="item in membershipOptions"
              :key="item.department_id"
              :label="item.department_name"
              :value="item.department_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="知识库名称">
          <el-input v-model="createForm.name" placeholder="例如：研发规范库" />
        </el-form-item>
        <el-form-item label="知识库编码">
          <el-input v-model="createForm.code" placeholder="例如：rd-standards" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述该空间承载的知识范围和使用方式"
          />
        </el-form-item>
        <el-form-item label="默认可见性">
          <el-radio-group v-model="createForm.visibility_scope">
            <el-radio-button
              v-for="option in knowledgeBaseVisibilityOptions"
              :key="option.value"
              :label="option.value"
            >
              {{ option.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingKnowledgeBase" @click="handleCreateKnowledgeBase">
          创建空间
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="shareDialogVisible" title="发起知识库共享申请" width="560px">
      <el-form label-position="top">
        <el-form-item label="知识库空间">
          <el-input :model-value="selectedKnowledgeBaseForShare?.name || ''" disabled />
        </el-form-item>
        <el-form-item label="目标部门">
          <el-tree-select
            v-model="shareForm.target_department_id"
            :data="departmentTree"
            node-key="id"
            check-strictly
            default-expand-all
            :props="{ label: 'name', children: 'children', value: 'id' }"
            placeholder="请选择共享目标部门"
          />
        </el-form-item>
        <el-form-item label="申请理由">
          <el-input
            v-model="shareForm.reason"
            type="textarea"
            :rows="4"
            placeholder="说明共享目的、使用场景和协作原因"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="shareDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingShareRequest" @click="handleCreateShareRequest">
          提交共享申请
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.document-hero {
  align-items: center;
}

.document-hero__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
}

.center-tabs :deep(.el-tabs__header) {
  margin-bottom: 22px;
}

.table-header,
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.table-header strong,
.section-head strong {
  display: block;
  color: var(--page-green-deep);
}

.table-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.kb-grid {
  display: grid;
  gap: 16px;
}

.kb-card {
  border: 1px solid rgba(24, 54, 48, 0.1);
  border-radius: 22px;
  padding: 20px;
  background: rgba(255, 253, 248, 0.94);
}

.kb-card__top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.kb-card__top strong {
  display: block;
  color: var(--page-green-deep);
  font-size: 20px;
}

.kb-card__top p {
  margin: 10px 0 0;
  color: var(--page-muted);
  line-height: 1.7;
}

.kb-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 16px;
  color: var(--page-muted);
  font-size: 13px;
}

.kb-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.kb-card__share {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed rgba(24, 54, 48, 0.12);
}

.kb-card__share-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--page-muted);
  font-size: 13px;
}

.kb-card__share-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.kb-card__share-empty {
  display: block;
  margin-top: 12px;
  color: var(--page-muted);
  font-size: 13px;
}

.soft-card--inner {
  border: 1px solid rgba(24, 54, 48, 0.08);
}

.upload-alert {
  margin-bottom: 18px;
  border-radius: 18px;
}

.upload-form {
  margin-bottom: 18px;
}

.upload-result {
  margin-top: 20px;
}

.el-upload__tip {
  margin-top: 12px;
  color: #6f7169;
}

@media (max-width: 960px) {
  .document-hero,
  .table-header,
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .document-hero__actions,
  .table-header__actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
