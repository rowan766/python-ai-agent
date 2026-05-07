<template>
  <div class="document-processing">
    <div class="document-layout">
      <el-card class="document-main-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div class="card-header__title">
              <div class="card-title-main">
                <el-icon><DocumentCopy /></el-icon>
                <span>文档处理</span>
              </div>
              <div class="status-chips">
                <el-tag type="primary" effect="plain">队列: {{ queueStatus.queueName || 'document-processing' }}</el-tag>
                <el-tag type="warning" effect="plain">待处理: {{ queueStatus.pendingCount }}</el-tag>
                <el-tag type="primary" effect="plain">处理中: {{ queueStatus.processingCount }}</el-tag>
                <el-tag type="success" effect="plain">模式: {{ queueModeLabel }}</el-tag>
              </div>
            </div>

            <el-breadcrumb separator="/" class="page-breadcrumb">
              <el-breadcrumb-item>首页</el-breadcrumb-item>
              <el-breadcrumb-item>资源管理</el-breadcrumb-item>
              <el-breadcrumb-item>文档处理</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </template>

        <CrudToolbar>
          <template #search>
            <el-form :inline="true" :model="searchForm">
              <el-form-item>
                <el-input v-model="searchForm.keyword" placeholder="请输入文档标题" clearable class="toolbar-input">
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item>
                <el-select v-model="searchForm.spaceId" clearable placeholder="知识空间" class="toolbar-select toolbar-select-wide">
                  <el-option
                    v-for="item in knowledgeSpaceOptions"
                    :key="item.id"
                    :label="item.name"
                    :value="item.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-select v-model="searchForm.status" clearable placeholder="处理状态" class="toolbar-select">
                  <el-option label="待处理" value="pending" />
                  <el-option label="处理中" value="processing" />
                  <el-option label="成功" value="success" />
                  <el-option label="失败" value="failed" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <CrudButton tone="blue" :icon="Search" @click="handleSearch">搜索</CrudButton>
                <CrudButton style-type="secondary" tone="gray" :icon="Refresh" @click="handleReset">重置</CrudButton>
              </el-form-item>
            </el-form>
          </template>

          <template #actions>
            <CrudButton v-permission="'knowledge:document:upload'" tone="blue" :icon="UploadFilled" @click="uploadDialogVisible = true">上传文档</CrudButton>
            <CrudButton tone="gray" :icon="RefreshRight" @click="refreshAll">刷新状态</CrudButton>
          </template>
        </CrudToolbar>

        <el-alert
          v-if="showWorkerNotice"
          class="worker-alert"
          type="warning"
          :closable="false"
          show-icon
          title="当前有待处理文档，但没有检测到正在处理中的任务。请确认独立 Worker 已启动，或直接使用 docker compose 一键启动整套服务。"
        />

        <CrudTable
          :data="tableData"
          :loading="loading"
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          :show-summary="true"
          :summary-icon="Files"
          :summary-text="`共 ${pagination.total} 份文档`"
          @update:current-page="pagination.page = $event"
          @update:page-size="pagination.pageSize = $event"
          @page-size-change="handlePageChange"
          @page-current-change="handlePageChange"
        >
          <el-table-column prop="title" label="文档标题" min-width="220" show-overflow-tooltip />
          <el-table-column label="所属空间" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.space?.name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="fileName" label="文件名" min-width="200" show-overflow-tooltip />
          <el-table-column prop="mimeType" label="文件类型" min-width="170" show-overflow-tooltip />
          <el-table-column label="文件大小" width="110" align="center">
            <template #default="{ row }">
              {{ formatFileSize(row.fileSize) }}
            </template>
          </el-table-column>
          <el-table-column label="处理状态" width="110" align="center">
            <template #default="{ row }">
              <el-tooltip v-if="row.status === 'failed' && row.errorMessage" :content="row.errorMessage" placement="top" :show-after="300">
                <el-tag :type="getStatusTagType(row.status)" effect="light" style="cursor: help;">{{ getStatusText(row.status) }}</el-tag>
              </el-tooltip>
              <el-tag v-else :type="getStatusTagType(row.status)" effect="light">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="解析反馈" width="140" align="center">
            <template #default="{ row }">
              <el-tag :type="getParseModeTagType(row.parseMode)" effect="light">
                {{ getParseModeText(row.parseMode) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="chunkCount" label="切片数" width="90" align="center" />
          <el-table-column prop="textLength" label="文本长度" width="110" align="center" />
          <el-table-column prop="processedAt" label="处理完成时间" min-width="170" align="center" />
          <el-table-column prop="createdAt" label="上传时间" min-width="170" align="center" />
          <el-table-column label="操作" width="340" fixed="right" align="center">
            <template #default="{ row }">
              <div class="table-actions">
                <CrudButton style-type="primary" size-variant="table" tone="blue" :icon="View" @click="handleOpenDetail(row)">详情</CrudButton>
                <CrudButton
                  v-permission="'knowledge:document:reprocess'"
                  style-type="primary"
                  size-variant="table"
                  tone="green"
                  :icon="RefreshRight"
                  :disabled="row.status === 'processing'"
                  @click="handleReprocess(row)"
                >
                  重试
                </CrudButton>
                <CrudButton
                  v-permission="'knowledge:document:download'"
                  style-type="primary"
                  size-variant="table"
                  tone="gray"
                  :icon="Download"
                  @click="handleDownload(row)"
                >
                  下载
                </CrudButton>
                <CrudButton
                  v-permission="'knowledge:document:delete'"
                  style-type="primary"
                  size-variant="table"
                  tone="red"
                  :icon="Delete"
                  :disabled="row.status === 'processing'"
                  @click="handleDelete(row)"
                >
                  删除
                </CrudButton>
              </div>
            </template>
          </el-table-column>
        </CrudTable>
      </el-card>

      <div class="side-panel">
        <el-card class="search-card" shadow="never">
          <template #header>
            <div class="side-card-header">
              <div class="side-card-title">
                <el-icon><Connection /></el-icon>
                <span>切片检索</span>
              </div>
            </div>
          </template>

          <el-input
            v-model="searchQuery"
            type="textarea"
            :rows="3"
            resize="none"
            placeholder="输入问题或关键词，例如：桥梁裂缝维修规范"
          />
          <div class="search-card__actions">
            <CrudButton tone="blue" :icon="Search" :loading="searchLoading" @click="handleSemanticSearch">开始检索</CrudButton>
            <CrudButton style-type="secondary" tone="gray" :icon="Refresh" @click="handleClearSearch">清空结果</CrudButton>
          </div>

          <div class="search-result-list">
            <div v-if="searchResults.length" class="search-result-count">命中 {{ searchResults.length }} 条相关切片</div>
            <el-empty v-else description="先输入检索词，我们就能看到 Qdrant 返回的相关切片。" />

            <div
              v-for="item in searchResults"
              :key="`${item.chunkId}-${item.score}`"
              class="search-result-item"
            >
              <div class="search-result-item__meta">
                <strong>{{ item.document?.title || `文档 #${item.documentId}` }}</strong>
                <span>空间 {{ item.document?.space?.name || '-' }}</span>
                <span>切片 {{ item.chunkIndex }}</span>
                <span>得分 {{ Number(item.score || 0).toFixed(4) }}</span>
              </div>
              <div class="search-result-item__content">
                <p>{{ getSearchPreview(item.content) }}</p>
              </div>
              <div class="search-result-item__footer">
                <el-button link type="primary" @click="handleOpenSearchResult(item)">更多</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <el-drawer
      v-model="detailDrawerVisible"
      title="文档详情"
      size="62%"
      @closed="handleDetailDrawerClosed"
    >
      <div v-loading="detailLoading" class="detail-drawer">
        <el-descriptions v-if="documentDetail" :column="2" border class="detail-descriptions">
          <el-descriptions-item label="文档标题">{{ documentDetail.title }}</el-descriptions-item>
          <el-descriptions-item label="文件名">{{ documentDetail.fileName }}</el-descriptions-item>
          <el-descriptions-item label="所属空间">{{ documentDetail.space?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="处理状态">
            <el-tag :type="getStatusTagType(documentDetail.status)" effect="light">
              {{ getStatusText(documentDetail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="解析反馈">
            <el-tag :type="getParseModeTagType(documentDetail.parseMode)" effect="light">
              {{ getParseModeText(documentDetail.parseMode) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="切片数量">{{ documentDetail.chunkCount }}</el-descriptions-item>
          <el-descriptions-item label="文本长度">{{ documentDetail.textLength }}</el-descriptions-item>
          <el-descriptions-item label="处理时间">{{ documentDetail.processedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="错误信息" :span="2">
            {{ documentDetail.errorMessage || '暂无' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-tabs class="detail-tabs">
          <el-tab-pane label="处理任务">
            <el-table :data="documentDetail?.tasks || []" border class="detail-table">
              <el-table-column prop="id" label="任务ID" width="100" align="center" />
              <el-table-column prop="taskType" label="任务类型" width="120" align="center" />
              <el-table-column label="状态" width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="getStatusTagType(row.status)" effect="light">{{ getStatusText(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="attempts" label="重试次数" width="100" align="center" />
              <el-table-column prop="startedAt" label="开始时间" min-width="160" align="center" />
              <el-table-column prop="finishedAt" label="完成时间" min-width="160" align="center" />
              <el-table-column prop="errorMessage" label="异常信息" min-width="220" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="文档切片">
            <el-table :data="chunkList" border class="detail-table">
              <el-table-column prop="chunkIndex" label="切片序号" width="100" align="center" />
              <el-table-column prop="contentLength" label="长度" width="90" align="center" />
              <el-table-column prop="charStart" label="起始位置" width="110" align="center" />
              <el-table-column prop="charEnd" label="结束位置" width="110" align="center" />
              <el-table-column prop="content" label="切片内容" min-width="420" show-overflow-tooltip />
            </el-table>

            <div class="chunk-pagination">
              <el-pagination
                :current-page="chunkPagination.page"
                :page-size="chunkPagination.pageSize"
                layout="prev, pager, next"
                :total="chunkPagination.total"
                @current-change="handleChunkPageChange"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>

    <el-dialog
      v-model="uploadDialogVisible"
      title="上传文档"
      width="580px"
      :close-on-click-modal="false"
      @closed="handleUploadDialogClosed"
    >
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadFormRules" label-position="top">
        <el-form-item label="知识空间" prop="spaceId">
          <el-select
            v-model="uploadForm.spaceId"
            placeholder="请选择目标知识空间"
            style="width: 100%"
          >
            <el-option
              v-for="item in knowledgeSpaceOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件" required>
          <div class="upload-drag-wrapper">
            <el-upload
              ref="uploadFileRef"
              multiple
              :limit="20"
              :auto-upload="false"
              :on-change="handleUploadFileChange"
              :on-remove="handleUploadFileRemove"
              :before-upload="beforeFileUpload"
              :on-exceed="handleUploadExceed"
              drag
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">将文件拖到此处，或<em>点击选择</em></div>
              <template #tip>
                <div class="el-upload__tip">支持 txt / pdf / docx / xlsx / pptx / 图片等格式，单个文件不超过 100MB，最多 20 个文件</div>
              </template>
            </el-upload>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="uploadSubmitting" :disabled="uploadFileList.length === 0" @click="handleSubmitUpload">
            确认上传 ({{ uploadFileList.length }})
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Connection,
  Delete,
  DocumentCopy,
  Download,
  Files,
  Refresh,
  RefreshRight,
  Search,
  UploadFilled,
  View
} from '@element-plus/icons-vue'
import CrudButton from '../../components/crud/CrudButton.vue'
import CrudTable from '../../components/crud/CrudTable.vue'
import CrudToolbar from '../../components/crud/CrudToolbar.vue'
import {
  deleteDocument,
  getDocumentChunks,
  getDocumentDetail,
  getDocumentList,
  getDocumentQueueStatus,
  reprocessDocument,
  searchDocumentChunks
} from '../../api/document'
import { getKnowledgeSpaceList } from '../../api/knowledge-space'
import { downloadFileBlob, uploadFiles } from '../../api/upload'

const loading = ref(false)
const searchLoading = ref(false)
const detailLoading = ref(false)
const detailDrawerVisible = ref(false)
const tableData = ref([])
const knowledgeSpaceOptions = ref([])
const documentDetail = ref(null)
const chunkList = ref([])
const searchResults = ref([])
const searchQuery = ref('')
const searchPreviewVisible = ref(false)
const activeSearchResult = ref(null)
const queueStatus = reactive({
  queueName: 'document-processing',
  processingMode: 'worker',
  pendingCount: 0,
  processingCount: 0
})

const searchForm = reactive({
  keyword: '',
  status: '',
  spaceId: undefined,
})
const uploadDialogVisible = ref(false)
const uploadSubmitting = ref(false)
const uploadFileRef = ref(null)
const uploadFormRef = ref(null)
const uploadFileList = ref([])
const uploadForm = reactive({
  spaceId: undefined,
})
const uploadFormRules = {
  spaceId: [{ required: true, message: '请选择知识空间', trigger: 'change' }],
}

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const chunkPagination = reactive({
  page: 1,
  pageSize: 8,
  total: 0
})

const currentDetailDocumentId = ref(null)
const wsConnected = ref(false)
let pollingTimer = null
let fastPollingTimer = null
let ws = null
let wsReconnectTimer = null
let wsMounted = false

const hasProcessingDocuments = computed(() => tableData.value.some((item) => ['pending', 'processing'].includes(item.status)))
const queueModeLabel = computed(() => {
  if (queueStatus.processingMode === 'worker') {
    return '独立 Worker'
  }
  return queueStatus.processingMode || '-'
})
const showWorkerNotice = computed(() => {
  return queueStatus.processingMode === 'worker' && queueStatus.pendingCount > 0 && queueStatus.processingCount === 0
})

const normalizePagedList = (response) => {
  const payload = response?.data ?? response ?? {}
  return {
    list: payload.list || [],
    total: payload.total || 0
  }
}

const normalizeResponseArray = (response) => {
  const payload = response?.data ?? response
  return Array.isArray(payload) ? payload : []
}

const formatFileSize = (size = 0) => {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  if (size < 1024 * 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MB`
  return `${(size / 1024 / 1024 / 1024).toFixed(1)} GB`
}

const getStatusText = (status) => {
  const statusMap = {
    pending: '待处理',
    processing: '处理中',
    success: '成功',
    failed: '失败'
  }
  return statusMap[status] || status || '-'
}

const getStatusTagType = (status) => {
  const tagMap = {
    pending: 'warning',
    processing: 'primary',
    success: 'success',
    failed: 'danger'
  }
  return tagMap[status] || 'info'
}

const getParseModeText = (parseMode) => {
  const parseModeMap = {
    auto: '自动识别',
    text_direct: '文本提取成功',
    pdf_text: 'PDF 文本提取成功',
    pdf_ocr_fallback: 'OCR 回退成功',
    image_ocr: 'OCR 识别成功',
    docx_text: 'Word 提取成功',
    excel_text: 'Excel 提取成功',
    pptx_text: 'PPT 提取成功',
  }
  return parseModeMap[parseMode] || parseMode || '-'
}

const getParseModeTagType = (parseMode) => {
  const parseModeTypeMap = {
    auto: 'info',
    text_direct: 'success',
    pdf_text: 'success',
    pdf_ocr_fallback: 'warning',
    image_ocr: 'primary',
    docx_text: 'success',
    excel_text: 'success',
    pptx_text: 'success',
  }
  return parseModeTypeMap[parseMode] || 'info'
}

const getSearchPreview = (content = '') => {
  const normalized = String(content).replace(/\s+/g, ' ').trim()
  if (normalized.length <= 96) {
    return normalized
  }
  return `${normalized.slice(0, 96)}...`
}

const fetchQueueStatus = async () => {
  try {
    const response = await getDocumentQueueStatus()
    const payload = response?.data || response || {}
    queueStatus.queueName = payload.queueName || 'document-processing'
    queueStatus.processingMode = payload.processingMode || 'worker'
    queueStatus.pendingCount = payload.pendingCount || 0
    queueStatus.processingCount = payload.processingCount || 0
  } catch (error) {
    queueStatus.pendingCount = 0
    queueStatus.processingCount = 0
  }
}

const fetchDocumentList = async () => {
  loading.value = true
  try {
    const response = await getDocumentList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
      status: searchForm.status || undefined,
      spaceId: searchForm.spaceId || undefined,
    })
    const { list, total } = normalizePagedList(response)
    tableData.value = list
    pagination.total = total
  } catch (error) {
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

const fetchKnowledgeSpaceOptions = async () => {
  try {
    const response = await getKnowledgeSpaceList({ page: 1, pageSize: 200, status: 1 })
    const payload = response?.data ?? response ?? {}
    knowledgeSpaceOptions.value = payload.list || []
  } catch {
    knowledgeSpaceOptions.value = []
  }
}

const fetchDocumentDetail = async (documentId) => {
  detailLoading.value = true
  try {
    const [detailResponse, chunkResponse] = await Promise.all([
      getDocumentDetail(documentId),
      getDocumentChunks(documentId, {
        page: chunkPagination.page,
        pageSize: chunkPagination.pageSize
      })
    ])
    documentDetail.value = detailResponse?.data || detailResponse || null
    const chunkPayload = normalizePagedList(chunkResponse)
    chunkList.value = chunkPayload.list
    chunkPagination.total = chunkPayload.total
  } catch (error) {
    documentDetail.value = null
    chunkList.value = []
    chunkPagination.total = 0
  } finally {
    detailLoading.value = false
  }
}

const refreshAll = async () => {
  await Promise.all([fetchQueueStatus(), fetchDocumentList()])
  if (detailDrawerVisible.value && currentDetailDocumentId.value) {
    await fetchDocumentDetail(currentDetailDocumentId.value)
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchDocumentList()
}

const handleReset = () => {
  searchForm.keyword = ''
  searchForm.status = ''
  searchForm.spaceId = undefined
  handleSearch()
}

const beforeFileUpload = (file) => {
  const isValidSize = file.size / 1024 / 1024 <= 100
  if (!isValidSize) {
    ElMessage.warning('文件大小不能超过 100MB')
    return false
  }
  return true
}

const handleUploadExceed = () => {
  ElMessage.warning('最多一次选择 20 个文件')
}

const stopFastPolling = () => {
  if (fastPollingTimer !== null) {
    window.clearInterval(fastPollingTimer)
    fastPollingTimer = null
  }
}

const startFastPolling = () => {
  stopFastPolling()
  let rounds = 0
  fastPollingTimer = window.setInterval(async () => {
    rounds++
    await fetchQueueStatus()
    await fetchDocumentList()
    if (detailDrawerVisible.value && currentDetailDocumentId.value) {
      await fetchDocumentDetail(currentDetailDocumentId.value)
    }
    const settled = !hasProcessingDocuments.value && queueStatus.pendingCount === 0
    if (settled || rounds >= 20) {
      stopFastPolling()
    }
  }, 3000)
}

const handleUploadFileChange = (file, fileList) => {
  uploadFileList.value = fileList.map(f => f.raw || f)
}

const handleUploadFileRemove = (file, fileList) => {
  uploadFileList.value = fileList.map(f => f.raw || f)
}

const handleUploadDialogClosed = () => {
  uploadFileList.value = []
  uploadForm.spaceId = undefined
  if (uploadFileRef.value) {
    uploadFileRef.value.clearFiles()
  }
}

const handleSubmitUpload = async () => {
  if (!uploadFileList.value.length) return
  try {
    await uploadFormRef.value?.validate()
  } catch {
    return
  }
  uploadSubmitting.value = true
  try {
    const formData = new FormData()
    uploadFileList.value.forEach(file => { formData.append('files', file) })
    if (uploadForm.spaceId) {
      formData.append('spaceId', uploadForm.spaceId)
    }
    const response = await uploadFiles(formData)
    const uploaded = normalizeResponseArray(response)
    if (!uploaded.length) throw new Error('文档上传失败')
    ElMessage.success(`已上传 ${uploaded.length} 个文件并入库`)
    uploadDialogVisible.value = false
    await refreshAll()
    if (!wsConnected.value) startFastPolling()
  } catch (error) {
    // error handled by interceptor
  } finally {
    uploadSubmitting.value = false
  }
}

const handleOpenDetail = async (row) => {
  currentDetailDocumentId.value = row.id
  chunkPagination.page = 1
  detailDrawerVisible.value = true
  await fetchDocumentDetail(row.id)
}

const handleDetailDrawerClosed = () => {
  currentDetailDocumentId.value = null
  documentDetail.value = null
  chunkList.value = []
  chunkPagination.page = 1
  chunkPagination.total = 0
}

const handleChunkPageChange = async (page) => {
  chunkPagination.page = page
  if (currentDetailDocumentId.value) {
    await fetchDocumentDetail(currentDetailDocumentId.value)
  }
}

const handleReprocess = async (row) => {
  try {
    await ElMessageBox.confirm(`确定重新处理文档“${row.title}”吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    const response = await reprocessDocument(row.id, { force: true })
    ElMessage.success(response?.message || '文档已重新入队')
    await refreshAll()
  } catch (error) {
    if (error !== 'cancel') {
      // 错误提示由拦截器处理
    }
  }
}

const handleDownload = async (row) => {
  try {
    const blob = await downloadFileBlob(row.fileId)
    const downloadUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = row.fileName || `document-${row.id}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(downloadUrl)
  } catch (error) {
    // 错误提示由拦截器处理
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除文档“${row.title}”吗？删除后会同时清理 MinIO 文件、向量索引和数据库关联数据，且无法恢复。`,
      '删除文档',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    const response = await deleteDocument(row.id)
    ElMessage.success(response?.message || '文档已删除')

    if (currentDetailDocumentId.value === row.id) {
      detailDrawerVisible.value = false
      handleDetailDrawerClosed()
    }

    searchResults.value = searchResults.value.filter((item) => item.documentId !== row.id)
    if (activeSearchResult.value?.documentId === row.id) {
      activeSearchResult.value = null
      searchPreviewVisible.value = false
    }

    if (tableData.value.length === 1 && pagination.page > 1) {
      pagination.page -= 1
    }

    await refreshAll()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      // 错误提示由拦截器处理
    }
  }
}

const handleSemanticSearch = async () => {
  const keyword = searchQuery.value.trim()
  if (!keyword) {
    ElMessage.warning('请输入检索词')
    return
  }

  searchLoading.value = true
  try {
    const response = await searchDocumentChunks({
      query: keyword,
      limit: 8,
      spaceId: searchForm.spaceId || undefined,
    })
    searchResults.value = normalizeResponseArray(response)
  } catch (error) {
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

const handleOpenSearchResult = (item) => {
  activeSearchResult.value = item
  searchPreviewVisible.value = true
}

const handleClearSearch = () => {
  searchQuery.value = ''
  searchResults.value = []
  activeSearchResult.value = null
  searchPreviewVisible.value = false
}

const handlePageChange = () => {
  fetchDocumentList()
}

const startPolling = () => {
  pollingTimer = window.setInterval(async () => {
    await fetchQueueStatus()
    // WebSocket 已连接时只刷新队列状态；断连时兜底刷列表
    if (!wsConnected.value && (queueStatus.pendingCount > 0 || hasProcessingDocuments.value)) {
      await fetchDocumentList()
      if (detailDrawerVisible.value && currentDetailDocumentId.value) {
        await fetchDocumentDetail(currentDetailDocumentId.value)
      }
    }
  }, 15000)
}

const handleDocumentStatusChange = async (message) => {
  // 先在内存中更新该文档状态，不等接口返回就立刻让用户看到变化
  const idx = tableData.value.findIndex((d) => d.id === message.documentId)
  if (idx !== -1) {
    tableData.value[idx] = {
      ...tableData.value[idx],
      status: message.status,
      errorMessage: message.errorMessage || null,
    }
  }
  await fetchQueueStatus()
  // 成功时拉一次完整列表（更新 chunkCount / textLength 等字段）
  if (message.status === 'success') {
    await fetchDocumentList()
  }
  if (detailDrawerVisible.value && currentDetailDocumentId.value === message.documentId) {
    await fetchDocumentDetail(message.documentId)
  }
}

const buildWsUrl = () => {
  const token = localStorage.getItem('token') || ''
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const apiBase = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
  const wsBase = /^https?:\/\//.test(apiBase)
    ? apiBase.replace(/^http/, 'ws')
    : `${protocol}//${window.location.host}${apiBase}`
  return `${wsBase}/ws/documents?token=${encodeURIComponent(token)}`
}

const connectWebSocket = () => {
  if (!wsMounted) return
  if (ws && ws.readyState <= WebSocket.OPEN) return
  const token = localStorage.getItem('token') || ''
  if (!token) return

  ws = new WebSocket(buildWsUrl())

  ws.onopen = () => {
    wsConnected.value = true
    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer)
      wsReconnectTimer = null
    }
  }

  ws.onmessage = async (event) => {
    try {
      const message = JSON.parse(event.data)
      if (message.type === 'document_status_changed') {
        await handleDocumentStatusChange(message)
      }
    } catch (_) { /* ignore */ }
  }

  ws.onclose = () => {
    wsConnected.value = false
    ws = null
    if (wsMounted) {
      wsReconnectTimer = setTimeout(connectWebSocket, 5000)
    }
  }

  ws.onerror = () => { ws?.close() }
}

const disconnectWebSocket = () => {
  wsMounted = false
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  wsConnected.value = false
}

onMounted(async () => {
  wsMounted = true
  await fetchKnowledgeSpaceOptions()
  await refreshAll()
  startPolling()
  connectWebSocket()
})

onUnmounted(() => {
  if (pollingTimer) window.clearInterval(pollingTimer)
  stopFastPolling()
  disconnectWebSocket()
})
</script>

<style scoped>
.document-processing {
  padding: 0;
}

.document-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
}

.document-main-card,
.search-card {
  border: none;
  border-radius: 20px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.06);
}

.card-header,
.card-header__title,
.card-title-main,
.side-card-header,
.side-card-title {
  display: flex;
  align-items: center;
}

.card-header,
.side-card-header {
  justify-content: space-between;
  gap: 12px;
}

.card-header__title {
  gap: 12px;
  flex-wrap: wrap;
}

.card-title-main,
.side-card-title {
  gap: 8px;
  color: #1f2a37;
  font-weight: 700;
}

.status-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.page-breadcrumb {
  color: #8a9aae;
}

.toolbar-input {
  width: 260px;
}

.toolbar-select {
  width: 150px;
}

.toolbar-select-wide {
  width: 190px;
}

.table-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.worker-alert {
  margin-bottom: 16px;
  border-radius: 12px;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-card__actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.search-result-list {
  margin-top: 18px;
  height: 520px;
  overflow-y: auto;
  padding-right: 4px;
}

.search-result-list::-webkit-scrollbar {
  width: 8px;
}

.search-result-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.4);
}

.search-result-count {
  margin-bottom: 10px;
  color: #718198;
  font-size: 13px;
}

.search-result-item {
  padding: 14px;
  border: 1px solid #e8eef6;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.search-result-item + .search-result-item {
  margin-top: 12px;
}

.search-result-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #7b8ba0;
}

.search-result-item__meta strong {
  color: #1f2a37;
  font-size: 13px;
}

.search-result-item p {
  margin: 0;
  line-height: 1.75;
  color: #4b5563;
  word-break: break-word;
}

.search-result-item__content {
  max-height: 96px;
  overflow-y: auto;
  padding-right: 4px;
}

.search-result-item__content::-webkit-scrollbar {
  width: 6px;
}

.search-result-item__content::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.45);
}

.search-result-item__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.search-preview-dialog {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-preview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #718198;
  font-size: 13px;
}

.search-preview-scroll {
  border: 1px solid #e8eef6;
  border-radius: 14px;
  background: #f8fbff;
}

.search-preview-text {
  margin: 0;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  color: #334155;
  font-size: 14px;
}

.detail-drawer {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-descriptions,
.detail-table {
  border-radius: 16px;
  overflow: hidden;
}

.detail-tabs {
  margin-top: 6px;
}

.chunk-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 1240px) {
  .document-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .toolbar-input,
  .toolbar-select,
  .toolbar-select-wide {
    width: 100%;
  }

  .search-card__actions {
    flex-wrap: wrap;
  }
}

/* 上传弹窗样式 */
.upload-drag-wrapper {
  width: 100%;
}

.upload-drag-wrapper :deep(.el-upload-dragger) {
  border-radius: 12px;
  padding: 28px 20px;
}

.upload-drag-wrapper :deep(.el-upload__text) {
  font-size: 14px;
  color: #6b7a8f;
}

.upload-drag-wrapper :deep(.el-upload__tip) {
  margin-top: 10px;
  font-size: 12px;
  color: #94a3b8;
}

.dialog-footer {
  display: flex;
  justify-content: center;
  gap: 16px;
}
</style>
