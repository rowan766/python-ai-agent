<template>
  <div class="document-qa">
    <div class="qa-layout">
      <el-card class="qa-main-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div class="card-header__title">
              <div class="card-title-main">
                <el-icon><ChatDotRound /></el-icon>
                <span>文档问答</span>
              </div>
              <div class="title-subtext">基于当前有权限访问的文档切片进行 RAG 问答</div>
            </div>

            <el-breadcrumb separator="/" class="page-breadcrumb">
              <el-breadcrumb-item>首页</el-breadcrumb-item>
              <el-breadcrumb-item>资源管理</el-breadcrumb-item>
              <el-breadcrumb-item>文档问答</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </template>

        <div class="qa-panel">
          <div class="qa-form">
            <el-form label-position="top">
              <el-form-item label="限定文档">
                <el-select
                  v-model="qaForm.documentId"
                  clearable
                  filterable
                  placeholder="默认检索全部可见文档"
                  class="qa-document-select"
                >
                  <el-option
                    v-for="item in documentOptions"
                    :key="item.id"
                    :label="item.title"
                    :value="item.id"
                  >
                    <div class="document-option">
                      <span class="document-option__title">{{ item.title }}</span>
                      <span class="document-option__meta">{{ item.chunkCount || 0 }} 个切片</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item label="你的问题">
                <el-input
                  v-model="qaForm.question"
                  type="textarea"
                  :rows="6"
                  resize="none"
                  maxlength="400"
                  show-word-limit
                  placeholder="例如：这份检测规则里关于 OCR 识别、裂缝处理或巡检标准有哪些关键信息？"
                />
              </el-form-item>

              <div class="quick-prompts">
                <button
                  v-for="prompt in quickPrompts"
                  :key="prompt"
                  type="button"
                  class="quick-prompt"
                  @click="handleUsePrompt(prompt)"
                >
                  {{ prompt }}
                </button>
              </div>

              <div class="qa-actions">
                <CrudButton tone="blue" :icon="Promotion" :loading="asking" @click="handleAsk">
                  开始问答
                </CrudButton>
                <CrudButton style-type="secondary" tone="gray" :icon="Refresh" @click="handleReset">
                  清空结果
                </CrudButton>
              </div>
            </el-form>
          </div>

          <el-divider />

          <div class="qa-answer-panel">
            <div class="answer-header">
              <div>
                <h3>回答结果</h3>
                <div class="answer-meta">
                  <el-tag type="primary" effect="plain">模式: {{ getAnswerModeLabel(answerData.answerMode) }}</el-tag>
                  <el-tag v-if="answerData.answerModel" type="warning" effect="plain">
                    模型: {{ answerData.answerModel }}
                  </el-tag>
                  <el-tag type="success" effect="plain">来源: {{ answerData.retrievalCount || answerData.sources.length }} 条</el-tag>
                </div>
              </div>
            </div>

            <el-empty
              v-if="!answerData.answer && !asking"
              description="输入问题后，我们会基于文档切片生成一版问答预览。"
            />

            <div v-else class="answer-content">
              <el-scrollbar max-height="320px" class="answer-scroll">
                <pre class="answer-text">{{ answerData.answer }}</pre>
              </el-scrollbar>
            </div>
          </div>
        </div>
      </el-card>

      <el-card class="qa-side-card" shadow="never">
        <template #header>
          <div class="side-card-title">
            <el-icon><DocumentCopy /></el-icon>
            <span>命中来源</span>
          </div>
        </template>

        <div class="sources-panel">
          <el-empty
            v-if="!answerData.sources.length"
            description="问答执行后，这里会展示当前回答引用的切片来源。"
          />

          <div
            v-for="source in answerData.sources"
            :key="`${source.chunkId}-${source.score}`"
            class="source-card"
          >
            <div class="source-card__meta">
              <strong>{{ source.documentTitle || `文档 #${source.documentId}` }}</strong>
              <span>切片 {{ source.chunkIndex ?? '-' }}</span>
              <span>得分 {{ Number(source.score || 0).toFixed(4) }}</span>
            </div>
            <div class="source-card__content">
              <p>{{ getSourcePreview(source.content) }}</p>
            </div>
            <div class="source-card__footer">
              <el-button link type="primary" @click="handleOpenSource(source)">查看全文</el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <el-dialog
      v-model="previewVisible"
      title="来源切片全文"
      width="760px"
    >
      <div class="source-preview">
        <div class="source-preview__meta">
          <span>{{ activeSource?.documentTitle || `文档 #${activeSource?.documentId || '-'}` }}</span>
          <span>切片 {{ activeSource?.chunkIndex ?? '-' }}</span>
          <span>得分 {{ Number(activeSource?.score || 0).toFixed(4) }}</span>
        </div>
        <el-scrollbar max-height="420px" class="source-preview__scroll">
          <pre class="source-preview__text">{{ activeSource?.content || '' }}</pre>
        </el-scrollbar>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, DocumentCopy, Promotion, Refresh } from '@element-plus/icons-vue'
import CrudButton from '../../components/crud/CrudButton.vue'
import { askDocumentQuestion, getDocumentList } from '../../api/document'

const asking = ref(false)
const documentOptions = ref([])
const previewVisible = ref(false)
const activeSource = ref(null)

const qaForm = reactive({
  documentId: null,
  question: '',
  limit: 4
})

const answerData = reactive({
  question: '',
  answer: '',
  answerMode: '',
  answerModel: '',
  retrievalCount: 0,
  sources: []
})

const quickPrompts = [
  '这批文档里最关键的检测规则是什么？',
  '请总结当前命中文档的核心结论。',
  '有哪些 OCR、巡检或处理流程相关的信息？',
  '请给我一版适合汇报的摘要。'
]

const getAnswerModeLabel = (mode) => {
  if (mode === 'llm-rag') {
    return 'LLM 生成回答'
  }
  if (mode === 'extractive-preview') {
    return '检索摘要回退'
  }
  return '未执行'
}

const getSourcePreview = (content = '') => {
  const normalized = String(content).replace(/\s+/g, ' ').trim()
  if (normalized.length <= 120) {
    return normalized
  }
  return `${normalized.slice(0, 120)}...`
}

const fetchDocumentOptions = async () => {
  try {
    const response = await getDocumentList({
      page: 1,
      pageSize: 200,
      status: 'success'
    })
    const payload = response?.data ?? response ?? {}
    documentOptions.value = payload.list || []
  } catch (error) {
    documentOptions.value = []
  }
}

const handleUsePrompt = (prompt) => {
  qaForm.question = prompt
}

const handleAsk = async () => {
  const question = qaForm.question.trim()
  if (!question) {
    ElMessage.warning('请输入问题')
    return
  }

  asking.value = true
  try {
    const response = await askDocumentQuestion({
      question,
      limit: qaForm.limit,
      documentId: qaForm.documentId || undefined
    })
    const payload = response?.data || response || {}
    answerData.question = payload.question || question
    answerData.answer = payload.answer || ''
    answerData.answerMode = payload.answerMode || ''
    answerData.answerModel = payload.answerModel || ''
    answerData.retrievalCount = Number(payload.retrievalCount || 0)
    answerData.sources = payload.sources || []
  } catch (error) {
    answerData.question = question
    answerData.answer = ''
    answerData.answerMode = ''
    answerData.answerModel = ''
    answerData.retrievalCount = 0
    answerData.sources = []
  } finally {
    asking.value = false
  }
}

const handleReset = () => {
  qaForm.documentId = null
  qaForm.question = ''
  answerData.question = ''
  answerData.answer = ''
  answerData.answerMode = ''
  answerData.answerModel = ''
  answerData.retrievalCount = 0
  answerData.sources = []
  activeSource.value = null
  previewVisible.value = false
}

const handleOpenSource = (source) => {
  activeSource.value = source
  previewVisible.value = true
}

onMounted(() => {
  fetchDocumentOptions()
})
</script>

<style scoped>
.document-qa {
  padding: 0;
}

.qa-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
  align-items: start;
}

.qa-main-card,
.qa-side-card {
  border: none;
  border-radius: 20px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.06);
}

.card-header,
.card-header__title,
.card-title-main,
.side-card-title,
.answer-header {
  display: flex;
  align-items: center;
}

.card-header,
.answer-header {
  justify-content: space-between;
  gap: 12px;
}

.card-header__title {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.card-title-main,
.side-card-title {
  gap: 8px;
  color: #1f2a37;
  font-weight: 700;
}

.title-subtext,
.page-breadcrumb {
  color: #8a9aae;
}

.qa-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 2px;
}

.quick-prompt {
  padding: 7px 12px;
  border: 1px solid #dce7f5;
  border-radius: 999px;
  background: #f8fbff;
  color: #44627f;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.quick-prompt:hover {
  border-color: #b7d0f3;
  background: #eef5ff;
  color: #245b9b;
}

.qa-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.qa-document-select {
  width: 100%;
}

.document-option {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.document-option__title {
  color: #1f2a37;
}

.document-option__meta {
  color: #8a9aae;
  font-size: 12px;
}

.answer-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.answer-content {
  margin-top: 8px;
}

.answer-scroll {
  border: 1px solid #e8eef6;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.answer-text {
  margin: 0;
  padding: 18px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.9;
  color: #334155;
  font-size: 14px;
}

.sources-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 480px;
}

.source-card {
  padding: 14px;
  border: 1px solid #e8eef6;
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.source-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #7b8ba0;
}

.source-card__meta strong {
  color: #1f2a37;
  font-size: 13px;
}

.source-card__content p {
  margin: 0;
  color: #4b5563;
  line-height: 1.8;
  word-break: break-word;
}

.source-card__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.source-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-preview__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #718198;
  font-size: 13px;
}

.source-preview__scroll {
  border: 1px solid #e8eef6;
  border-radius: 14px;
  background: #f8fbff;
}

.source-preview__text {
  margin: 0;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  color: #334155;
  font-size: 14px;
}

@media (max-width: 1240px) {
  .qa-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .qa-actions {
    flex-wrap: wrap;
  }
}
</style>
