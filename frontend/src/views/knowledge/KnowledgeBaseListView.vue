<script setup lang="ts">
import type { AxiosError } from 'axios'
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  createKnowledgeBase,
  createKnowledgeBaseShareRequest,
  fetchKnowledgeBaseShares,
  fetchKnowledgeBases,
  fetchMyKnowledgeBaseShareRequests,
} from '@/api/modules/knowledge'
import { fetchDepartmentTree } from '@/api/modules/organization'
import { useAuthStore } from '@/stores/auth'
import type { DepartmentNode } from '@/types/organization'
import type {
  CreateKnowledgeBasePayload,
  KnowledgeBaseItem,
  KnowledgeBaseShareItem,
} from '@/types/knowledge'
import { ElMessage } from 'element-plus'
import { formatVisibilityScope, getPreferredMembership } from '@/utils/organization'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const submitting = ref(false)
const shareSubmitting = ref(false)
const createDialogVisible = ref(false)
const shareDialogVisible = ref(false)
const knowledgeBases = ref<KnowledgeBaseItem[]>([])
const departmentTree = ref<DepartmentNode[]>([])
const shareMap = ref<Record<number, KnowledgeBaseShareItem[]>>({})
const myShareRequestCount = ref(0)
const selectedKnowledgeBaseForShare = ref<KnowledgeBaseItem | null>(null)
const memberships = computed(() => authStore.user?.memberships ?? [])
const preferredMembership = computed(() => getPreferredMembership(memberships.value))
const selectedDepartmentId = ref<number | undefined>(preferredMembership.value?.department_id)
const visibleDocumentCount = computed(() =>
  knowledgeBases.value.reduce((total, item) => total + item.document_count, 0),
)
const activeShareCount = computed(() =>
  Object.values(shareMap.value).reduce((total, items) => total + items.length, 0),
)

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
  { label: '本部门可见', value: 'department_private' },
  { label: '可以共享给相关部门', value: 'department_shared' },
  { label: '全组织可见', value: 'org_public' },
]

async function loadKnowledgeBases() {
  loading.value = true
  try {
    const [knowledgeBaseResult, departmentTreeResult, myShareResult] = await Promise.all([
      fetchKnowledgeBases(selectedDepartmentId.value),
      fetchDepartmentTree(),
      fetchMyKnowledgeBaseShareRequests(),
    ])

    knowledgeBases.value = knowledgeBaseResult.items
    departmentTree.value = departmentTreeResult.items
    myShareRequestCount.value = myShareResult.count

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

    if (!createForm.department_id && preferredMembership.value) {
      createForm.department_id = preferredMembership.value.department_id
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('读取知识空间失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  if (preferredMembership.value && !createForm.department_id) {
    createForm.department_id = preferredMembership.value.department_id
  }
  createDialogVisible.value = true
}

function openShareDialog(item: KnowledgeBaseItem) {
  selectedKnowledgeBaseForShare.value = item
  shareForm.target_department_id = undefined
  shareForm.reason = ''
  shareDialogVisible.value = true
}

function openDocuments(item: KnowledgeBaseItem) {
  void router.push({
    name: 'documents',
    query: { knowledgeBaseId: String(item.id) },
  })
}

function openUpload(item: KnowledgeBaseItem) {
  void router.push({
    name: 'document-upload',
    query: { knowledgeBaseId: String(item.id) },
  })
}

async function handleCreateKnowledgeBase() {
  if (!createForm.department_id) {
    ElMessage.warning('请先选择归属部门。')
    return
  }
  if (!createForm.name.trim() || !createForm.code.trim()) {
    ElMessage.warning('请补全空间名称和空间编码。')
    return
  }

  submitting.value = true
  try {
    await createKnowledgeBase({
      ...createForm,
      name: createForm.name.trim(),
      code: createForm.code.trim(),
      description: createForm.description?.trim() || '',
    })
    ElMessage.success('知识空间创建成功。')
    createDialogVisible.value = false
    createForm.code = ''
    createForm.name = ''
    createForm.description = ''
    createForm.visibility_scope = 'department_private'
    await loadKnowledgeBases()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '创建知识空间失败。')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

async function handleCreateShareRequest() {
  if (!selectedKnowledgeBaseForShare.value) {
    return
  }
  if (!shareForm.target_department_id || !shareForm.reason.trim()) {
    ElMessage.warning('请补全目标部门和共享原因。')
    return
  }

  shareSubmitting.value = true
  try {
    await createKnowledgeBaseShareRequest(selectedKnowledgeBaseForShare.value.id, {
      target_department_id: shareForm.target_department_id,
      reason: shareForm.reason.trim(),
    })
    ElMessage.success('共享申请已提交到目标部门审批。')
    shareDialogVisible.value = false
    await loadKnowledgeBases()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '提交共享申请失败。')
    console.error(error)
  } finally {
    shareSubmitting.value = false
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

watch(selectedDepartmentId, () => {
  void loadKnowledgeBases()
}, { immediate: true })
</script>

<template>
  <div class="page">
    <section class="hero-card knowledge-hero">
      <div>
        <p class="page-eyebrow">Knowledge Spaces</p>
        <h2>所有资料先进入明确的空间，再谈共享、审批和检索。</h2>
        <p class="page-copy">
          这里是知识工作的真正起点。先选当前工作部门，再进入对应空间看文档、上传资料或发起共享，不需要先理解全局治理结构。
        </p>
      </div>
      <div class="hero-card__summary">
        <span>{{ preferredMembership?.department_name || '未设置' }}</span>
        <small>当前优先工作部门</small>
        <el-button type="primary" @click="openCreateDialog">新建知识空间</el-button>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">当前可见空间</span>
        <strong>{{ knowledgeBases.length }}</strong>
        <p>已自动按你的组织归属和共享范围过滤。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">空间内文档</span>
        <strong>{{ visibleDocumentCount }}</strong>
        <p>当前列表中这些空间包含的文档总数。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">已生效共享</span>
        <strong>{{ activeShareCount }}</strong>
        <p>已经开放给其他部门使用的共享关系数量。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">我发起的共享</span>
        <strong>{{ myShareRequestCount }}</strong>
        <p>方便继续跟进跨部门协作的审批状态。</p>
      </el-card>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>
        <div class="section-head">
          <strong>空间列表</strong>
          <el-select
            v-model="selectedDepartmentId"
            clearable
            placeholder="按部门筛选"
            class="section-head__select"
          >
            <el-option
              v-for="membership in memberships"
              :key="membership.department_id"
              :label="membership.department_name"
              :value="membership.department_id"
            />
          </el-select>
        </div>
      </template>

      <el-skeleton v-if="loading" :rows="6" animated />

      <el-empty
        v-else-if="!knowledgeBases.length"
        description="当前范围内还没有知识空间。你可以先创建一个空间，再从那里开始上传资料。"
      />

      <div v-else class="kb-grid">
        <article v-for="item in knowledgeBases" :key="item.id" class="kb-card">
          <div class="kb-card__top">
            <div>
              <strong>{{ item.name }}</strong>
              <p>{{ item.description || '这个空间还没有补充说明。' }}</p>
            </div>
            <el-tag round>{{ formatVisibilityScope(item.visibility_scope) }}</el-tag>
          </div>

          <div class="kb-card__meta">
            <span>归属部门：{{ item.department_name }}</span>
            <span>空间编码：{{ item.code }}</span>
            <span>文档数：{{ item.document_count }}</span>
          </div>

          <div class="kb-card__actions">
            <el-button type="primary" plain @click="openDocuments(item)">查看文档</el-button>
            <el-button plain @click="openUpload(item)">上传到这里</el-button>
            <el-button link type="primary" @click="openShareDialog(item)">发起共享</el-button>
          </div>

          <div class="kb-card__share">
            <div class="kb-card__share-head">
              <span>已共享给</span>
            </div>
            <div v-if="shareMap[item.id]?.length" class="kb-card__share-tags">
              <el-tag
                v-for="share in shareMap[item.id]"
                :key="share.id"
                type="success"
                round
              >
                {{ share.target_department_name }}
              </el-tag>
            </div>
            <span v-else class="kb-card__share-empty">当前还没有生效的共享目标部门。</span>
          </div>
        </article>
      </div>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="新建知识空间" width="520px">
      <el-form label-position="top">
        <el-form-item label="归属部门">
          <el-select v-model="createForm.department_id" placeholder="请选择归属部门" style="width: 100%">
            <el-option
              v-for="membership in memberships"
              :key="membership.department_id"
              :label="membership.department_name"
              :value="membership.department_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="空间名称">
          <el-input v-model="createForm.name" placeholder="例如：产品运营作战室" />
        </el-form-item>
        <el-form-item label="空间编码">
          <el-input v-model="createForm.code" placeholder="例如：product-playbook" />
        </el-form-item>
        <el-form-item label="空间说明">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述这个空间承载的知识范围和适用场景"
          />
        </el-form-item>
        <el-form-item label="默认可见范围">
          <el-radio-group v-model="createForm.visibility_scope">
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

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreateKnowledgeBase">
          创建空间
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="shareDialogVisible" title="发起空间共享" width="560px">
      <el-form label-position="top">
        <el-form-item label="知识空间">
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
        <el-form-item label="共享原因">
          <el-input
            v-model="shareForm.reason"
            type="textarea"
            :rows="4"
            placeholder="说明为什么要把这个空间开放给目标部门"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="shareDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="shareSubmitting" @click="handleCreateShareRequest">
          提交共享申请
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.knowledge-hero {
  align-items: center;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-head strong {
  color: var(--page-green-deep);
}

.section-head__select {
  width: 220px;
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

@media (max-width: 960px) {
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .section-head__select {
    width: 100%;
  }
}
</style>
