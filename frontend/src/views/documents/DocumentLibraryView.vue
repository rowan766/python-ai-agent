<script setup lang="ts">
import { fetchKnowledgeBases, fetchKnowledgeDocuments } from '@/api/modules/knowledge'
import { fetchSupportedFormats } from '@/api/modules/rag'
import type { KnowledgeBaseItem, KnowledgeDocumentItem } from '@/types/knowledge'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'

const loading = ref(false)
const supportedFormats = ref<string[]>([])
const knowledgeBases = ref<KnowledgeBaseItem[]>([])
const documents = ref<KnowledgeDocumentItem[]>([])
const selectedKnowledgeBaseId = ref<number | undefined>(undefined)

const totalChunks = computed(() =>
  documents.value.reduce((total, item) => total + item.chunks_count, 0),
)

async function loadData() {
  loading.value = true
  try {
    const [formatResult, knowledgeBaseResult, documentResult] = await Promise.all([
      fetchSupportedFormats(),
      fetchKnowledgeBases(),
      fetchKnowledgeDocuments(
        selectedKnowledgeBaseId.value
          ? { knowledge_base_id: selectedKnowledgeBaseId.value }
          : undefined,
      ),
    ])
    supportedFormats.value = formatResult.supported_formats
    knowledgeBases.value = knowledgeBaseResult.items
    documents.value = documentResult.items
  } catch (error) {
    console.error(error)
    ElMessage.error('读取文档中心数据失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadData()
})
</script>

<template>
  <div class="page">
    <section class="hero-card">
      <div>
        <p class="page-eyebrow">Document Center</p>
        <h2>文档开始有了真正的业务归属，不再只是“传进去就进向量库”。</h2>
        <p class="page-copy">
          当前页面展示的是你有权限访问的知识文档。每篇文档都带着所属知识库、部门、上传人和切片数量，后续共享、审批和版本能力都会沿着这条主线扩展。
        </p>
      </div>
      <div class="hero-card__summary">
        <span>{{ documents.length }}</span>
        <small>当前可见文档数</small>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">知识空间数</span>
        <strong>{{ knowledgeBases.length }}</strong>
        <p>文档必须归属到知识库空间，便于权限控制和后续治理。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可见文档数</span>
        <strong>{{ documents.length }}</strong>
        <p>列表范围受当前用户组织归属和管理权限影响。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">已入库切片</span>
        <strong>{{ totalChunks }}</strong>
        <p>用于观察当前文档治理范围内的向量化内容规模。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">支持格式</span>
        <strong>{{ supportedFormats.length }}</strong>
        <p>上传页会直接读取同一组后端支持格式配置。</p>
      </el-card>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>
        <div class="table-header">
          <span>文档清单</span>
          <el-select
            v-model="selectedKnowledgeBaseId"
            clearable
            placeholder="按知识库筛选"
            style="width: 220px"
            @change="loadData"
          >
            <el-option
              v-for="item in knowledgeBases"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </div>
      </template>

      <el-table v-loading="loading" :data="documents" stripe>
        <el-table-column prop="title" label="文档标题" min-width="220" />
        <el-table-column prop="knowledge_base_name" label="知识库空间" min-width="180" />
        <el-table-column prop="department_name" label="归属部门" min-width="140" />
        <el-table-column prop="uploader_username" label="上传人" min-width="120" />
        <el-table-column prop="chunks_count" label="切片数" width="100" />
        <el-table-column prop="visibility_scope" label="可见性" min-width="160" />
        <el-table-column prop="file_extension" label="格式" width="100" />
      </el-table>

      <el-empty
        v-if="!loading && !documents.length"
        description="当前范围内还没有文档。可以先去上传文档页向某个知识库空间投递资料。"
      />
    </el-card>
  </div>
</template>

<style scoped>
.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
</style>
