<script setup lang="ts">
import { fetchKnowledgeBases } from '@/api/modules/knowledge'
import { queryKnowledge } from '@/api/modules/rag'
import type { KnowledgeBaseItem } from '@/types/knowledge'
import type { SearchResponse } from '@/types/rag'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

const form = reactive({
  query: 'Agent',
  limit: 5,
  knowledgeBaseId: undefined as number | undefined,
})

const loading = ref(false)
const response = ref<SearchResponse | null>(null)
const knowledgeBases = ref<KnowledgeBaseItem[]>([])

const quickQueries = ['Agent', 'FastAPI', 'Qdrant', 'upload test document']

onMounted(async () => {
  try {
    const result = await fetchKnowledgeBases()
    knowledgeBases.value = result.items
  } catch (error) {
    console.error(error)
  }
})

async function handleSearch() {
  if (!form.query.trim()) {
    ElMessage.warning('请输入检索关键词。')
    return
  }

  loading.value = true
  try {
    response.value = await queryKnowledge(form.query.trim(), form.limit, form.knowledgeBaseId)
  } catch (error) {
    ElMessage.error('检索失败，请确认后端服务、embedding 和向量检索状态。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

function applyQuickQuery(value: string) {
  form.query = value
  void handleSearch()
}
</script>

<template>
  <div class="page">
    <section class="hero-card">
      <div>
        <p class="page-eyebrow">RAG Search</p>
        <h2>这一步先接现有检索接口，后续再升级成真正的权限过滤式企业问答。</h2>
        <p class="page-copy">
          当前后端接口是 `/api/rag/query`。下一阶段会演进为 `rag/search` 与 `rag/ask`，并纳入部门、知识库空间、共享策略和审批状态过滤。
        </p>
      </div>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>执行检索</template>
      <el-form inline>
        <el-form-item label="知识库空间">
          <el-select
            v-model="form.knowledgeBaseId"
            clearable
            placeholder="默认检索全部可访问空间"
            style="width: 260px"
          >
            <el-option
              v-for="item in knowledgeBases"
              :key="item.id"
              :label="`${item.name} · ${item.department_name}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="form.query"
            placeholder="例如 Agent / FastAPI / Qdrant"
            style="width: 280px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="Top K">
          <el-input-number v-model="form.limit" :min="1" :max="20" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSearch">
            开始检索
          </el-button>
        </el-form-item>
      </el-form>

      <div class="quick-query-list">
        <span>推荐测试词：</span>
        <el-button
          v-for="item in quickQueries"
          :key="item"
          text
          @click="applyQuickQuery(item)"
        >
          {{ item }}
        </el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="soft-card">
      <template #header>
        检索结果
        <el-tag v-if="response" class="ml-12" round>{{ response.count }} 条命中</el-tag>
      </template>

      <el-empty
        v-if="!response"
        description="还没有执行检索，先试一个关键词。"
      />

      <div v-else-if="response.results.length" class="result-stack">
        <article v-for="(item, index) in response.results" :key="index" class="result-card">
          <div class="result-card__meta">
            <strong>命中片段 {{ index + 1 }}</strong>
            <el-tag type="success" round>score {{ item.score.toFixed(3) }}</el-tag>
          </div>
          <div class="result-card__source">
            <span v-if="item.metadata.department_name">部门：{{ item.metadata.department_name }}</span>
            <span v-if="item.metadata.knowledge_base_name">知识库：{{ item.metadata.knowledge_base_name }}</span>
            <span v-if="item.metadata.filename">来源：{{ item.metadata.filename }}</span>
          </div>
          <p>{{ item.content }}</p>
          <small v-if="item.metadata.retrieval_mode">
            召回方式：{{ item.metadata.retrieval_mode }}
          </small>
        </article>
      </div>

      <el-empty
        v-else
        description="当前没有结果。若是短词检索，也可以观察后端关键词兜底是否生效。"
      />
    </el-card>
  </div>
</template>

<style scoped>
.quick-query-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
  color: #6f7169;
}

.result-stack {
  display: grid;
  gap: 14px;
}

.result-card {
  border: 1px solid rgba(24, 54, 48, 0.1);
  border-radius: 18px;
  padding: 18px;
  background: rgba(255, 253, 248, 0.9);
}

.result-card__meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.result-card p {
  margin: 0;
  color: #2a322f;
  line-height: 1.8;
  white-space: pre-line;
}

.result-card__source {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
  color: #6f7169;
  font-size: 13px;
}

.result-card small {
  display: inline-block;
  margin-top: 10px;
  color: #8a6f37;
}
</style>
