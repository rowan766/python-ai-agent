<script setup lang="ts">
import type { AxiosError } from 'axios'
import { UploadFilled } from '@element-plus/icons-vue'
import { fetchKnowledgeBases, uploadKnowledgeDocument } from '@/api/modules/knowledge'
import { fetchSupportedFormats } from '@/api/modules/rag'
import type { KnowledgeBaseItem, UploadKnowledgeDocumentResponse } from '@/types/knowledge'
import type { UploadRequestOptions } from 'element-plus'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

const uploading = ref(false)
const supportedFormats = ref<string[]>([])
const knowledgeBases = ref<KnowledgeBaseItem[]>([])
const selectedKnowledgeBaseId = ref<number | undefined>(undefined)
const selectedVisibilityScope = ref('knowledge_base_default')
const uploadResult = ref<UploadKnowledgeDocumentResponse | null>(null)

const acceptValue = computed(() => supportedFormats.value.join(','))
const visibilityOptions = [
  { label: '沿用知识库默认策略', value: 'knowledge_base_default' },
  { label: '部门私有', value: 'department_private' },
  { label: '部门共享', value: 'department_shared' },
  { label: '全组织公开', value: 'org_public' },
]

onMounted(async () => {
  try {
    const [formatResult, knowledgeBaseResult] = await Promise.all([
      fetchSupportedFormats(),
      fetchKnowledgeBases(),
    ])
    supportedFormats.value = formatResult.supported_formats
    knowledgeBases.value = knowledgeBaseResult.items
    selectedKnowledgeBaseId.value = knowledgeBaseResult.items[0]?.id
  } catch (error) {
    console.error(error)
  }
})

async function handleUpload(options: UploadRequestOptions) {
  if (!selectedKnowledgeBaseId.value) {
    ElMessage.warning('请先选择归属知识库空间。')
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
    ElMessage.success(`上传成功，已生成 ${result.document.chunks_count} 个切片。`)
    options.onSuccess?.(result)
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    const detail =
      axiosError.response?.data?.detail ||
      axiosError.message ||
      '上传失败，请确认后端服务、模型配置和文件格式。'
    ElMessage.error(detail)
    console.error(error)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="page">
    <section class="hero-card">
      <div>
        <p class="page-eyebrow">Upload Pipeline</p>
        <h2>上传入口已经升级为“先选知识库空间，再完成解析与入库”。</h2>
        <p class="page-copy">
          当前后端接口使用 `/api/documents/upload`。上传成功后，文档会同时落到业务表和 Qdrant，后续检索可以按知识库空间和组织范围做过滤。
        </p>
      </div>
    </section>

    <section class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>上传文件</template>
        <el-alert
          v-if="!knowledgeBases.length"
          class="upload-alert"
          title="当前还没有可上传的知识库空间。请先完成组织接入，并由负责人创建至少一个知识库空间。"
          type="warning"
          :closable="false"
          show-icon
        />
        <el-form label-position="top" class="upload-form">
          <el-form-item label="归属知识库空间">
            <el-select
              v-model="selectedKnowledgeBaseId"
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

      <el-card shadow="never" class="soft-card">
        <template #header>当前链路说明</template>
        <el-timeline>
          <el-timeline-item timestamp="1">先选择归属知识库空间和文档可见性</el-timeline-item>
          <el-timeline-item timestamp="2">文件落到后端 `uploads/` 临时目录并按格式解析</el-timeline-item>
          <el-timeline-item timestamp="3">切片后使用 `text-embedding-v3` 分批生成向量</el-timeline-item>
          <el-timeline-item timestamp="4">文档实体入库，同时写入 Qdrant 并带上部门/空间/文档标识</el-timeline-item>
        </el-timeline>
      </el-card>
    </section>

    <el-card v-if="uploadResult" shadow="never" class="soft-card">
      <template #header>上传结果</template>
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
  </div>
</template>

<style scoped>
.upload-alert {
  margin-bottom: 18px;
  border-radius: 18px;
}

.upload-form {
  margin-bottom: 18px;
}

.el-upload__tip {
  margin-top: 12px;
  color: #6f7169;
}
</style>
