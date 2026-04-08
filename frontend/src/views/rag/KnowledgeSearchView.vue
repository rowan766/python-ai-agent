<script setup lang="ts">
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { fetchKnowledgeBases } from '@/api/modules/knowledge'
import { queryKnowledge } from '@/api/modules/rag'
import type { KnowledgeBaseItem } from '@/types/knowledge'
import type { SearchResponse } from '@/types/rag'

const loading = ref(false)
const response = ref<SearchResponse | null>(null)
const knowledgeBases = ref<KnowledgeBaseItem[]>([])

const searchForm = reactive({
  query: 'Agent',
  limit: 10,
  knowledgeBaseId: undefined as number | undefined,
})

const quickQueries = ['Agent', 'FastAPI', 'Qdrant', 'upload test document']
const resultCount = computed(() => response.value?.results.length ?? 0)

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message
  }

  return fallback
}

async function loadKnowledgeBaseOptions() {
  try {
    const result = await fetchKnowledgeBases()
    knowledgeBases.value = result.items
  } catch (error) {
    console.error(error)
  }
}

async function handleSearch() {
  if (!searchForm.query.trim()) {
    ElMessage.warning('请输入检索关键词。')
    return
  }

  loading.value = true
  try {
    response.value = await queryKnowledge(
      searchForm.query.trim(),
      searchForm.limit,
      searchForm.knowledgeBaseId,
    )
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '检索失败，请确认后端服务和向量检索状态。'))
    console.error(error)
  } finally {
    loading.value = false
  }
}

function applyQuickQuery(value: string) {
  searchForm.query = value
  void handleSearch()
}

onMounted(async () => {
  await loadKnowledgeBaseOptions()
})
</script>

<template>
  <div class="page">
    <section class="page-toolbar">
      <div class="page-toolbar__title">
        <h2>知识检索</h2>
        <span>{{ knowledgeBases.length }} 个空间可筛选</span>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">检索词</span>
        <strong class="summary-card__value">{{ searchForm.query || '--' }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">知识空间</span>
        <strong class="summary-card__value">
          {{
            knowledgeBases.find((item) => item.id === searchForm.knowledgeBaseId)?.name
            || '全部空间'
          }}
        </strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">返回条数</span>
        <strong class="summary-card__value">{{ resultCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">限制条数</span>
        <strong class="summary-card__value">{{ searchForm.limit }}</strong>
      </el-card>
    </section>

    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-toolbar">
          <strong>检索条件</strong>
          <div class="table-toolbar__filters">
            <el-select
              v-model="searchForm.knowledgeBaseId"
              clearable
              placeholder="全部知识空间"
              class="toolbar-field"
            >
              <el-option
                v-for="item in knowledgeBases"
                :key="item.id"
                :label="`${item.name} · ${item.department_name}`"
                :value="item.id"
              />
            </el-select>
            <el-input
              v-model="searchForm.query"
              placeholder="输入关键词"
              class="toolbar-field toolbar-field--wide"
              @keyup.enter="handleSearch"
            />
            <el-input-number v-model="searchForm.limit" :min="1" :max="20" />
            <el-button type="primary" :loading="loading" @click="handleSearch">
              开始检索
            </el-button>
          </div>
        </div>
      </template>

      <div class="quick-query-strip">
        <span>快捷检索</span>
        <el-button
          v-for="item in quickQueries"
          :key="item"
          text
          @click="applyQuickQuery(item)"
        >
          {{ item }}
        </el-button>
      </div>

      <el-empty v-if="!response && !loading" description="执行一次检索后显示结果" />

      <el-table
        v-else
        v-loading="loading"
        :data="response?.results ?? []"
        stripe
        empty-text="没有匹配结果"
      >
        <el-table-column label="命中内容" min-width="360">
          <template #default="{ row }">
            <div class="result-content">{{ row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column label="知识空间" min-width="180">
          <template #default="{ row }">
            {{ String(row.metadata.knowledge_base_name ?? '--') }}
          </template>
        </el-table-column>
        <el-table-column label="部门" min-width="140">
          <template #default="{ row }">
            {{ String(row.metadata.department_name ?? '--') }}
          </template>
        </el-table-column>
        <el-table-column label="文件名" min-width="180">
          <template #default="{ row }">
            {{ String(row.metadata.filename ?? '--') }}
          </template>
        </el-table-column>
        <el-table-column label="Score" width="120">
          <template #default="{ row }">
            {{ row.score.toFixed(3) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar-field {
  width: 220px;
}

.toolbar-field--wide {
  width: 320px;
}

.quick-query-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  color: var(--page-muted);
  font-size: 13px;
}

.result-content {
  color: #111827;
  line-height: 1.7;
  white-space: pre-line;
}

@media (max-width: 960px) {
  .toolbar-field,
  .toolbar-field--wide {
    width: 100%;
  }
}
</style>
