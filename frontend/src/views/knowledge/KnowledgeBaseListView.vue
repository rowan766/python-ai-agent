<script setup lang="ts">
import type { AxiosError } from 'axios'
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
  { label: '共享后可见', value: 'department_shared' },
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

function getShareTargets(knowledgeBaseId: number): string {
  const items = shareMap.value[knowledgeBaseId] ?? []
  if (!items.length) {
    return '--'
  }
  return items.map((item) => item.target_department_name).join('、')
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
      description: '',
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
    ElMessage.success('共享申请已提交。')
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

watch(
  selectedDepartmentId,
  () => {
    void loadKnowledgeBases()
  },
  { immediate: true },
)
</script>

<template>
  <div class="page">
    <section class="page-toolbar">
      <div class="page-toolbar__title">
        <h2>知识空间</h2>
        <span>当前部门：{{ preferredMembership?.department_name || '未设置' }}</span>
      </div>
      <div class="page-toolbar__actions">
        <el-button @click="router.push('/documents')">文档中心</el-button>
        <el-button type="primary" @click="openCreateDialog">新建空间</el-button>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">当前可见空间</span>
        <strong class="summary-card__value">{{ knowledgeBases.length }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">空间内文档</span>
        <strong class="summary-card__value">{{ visibleDocumentCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">已生效共享</span>
        <strong class="summary-card__value">{{ activeShareCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">我发起的共享</span>
        <strong class="summary-card__value">{{ myShareRequestCount }}</strong>
      </el-card>
    </section>

    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-toolbar">
          <strong>空间列表</strong>
          <div class="table-toolbar__filters">
            <el-select
              v-model="selectedDepartmentId"
              clearable
              placeholder="按部门筛选"
              class="toolbar-select"
            >
              <el-option
                v-for="membership in memberships"
                :key="membership.department_id"
                :label="membership.department_name"
                :value="membership.department_id"
              />
            </el-select>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="knowledgeBases" stripe empty-text="当前没有知识空间">
        <el-table-column prop="name" label="空间名称" min-width="180" />
        <el-table-column prop="code" label="空间编码" min-width="160" />
        <el-table-column prop="department_name" label="归属部门" min-width="140" />
        <el-table-column prop="document_count" label="文档数" width="100" />
        <el-table-column label="可见范围" min-width="140">
          <template #default="{ row }">
            {{ formatVisibilityScope(row.visibility_scope) }}
          </template>
        </el-table-column>
        <el-table-column label="已共享给" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ getShareTargets(row.id) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text @click="openDocuments(row)">文档</el-button>
            <el-button text @click="openUpload(row)">上传</el-button>
            <el-button text @click="openShareDialog(row)">共享</el-button>
          </template>
        </el-table-column>
      </el-table>
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
          <el-input v-model="createForm.name" placeholder="例如：产品运营资料库" />
        </el-form-item>
        <el-form-item label="空间编码">
          <el-input v-model="createForm.code" placeholder="例如：product-ops" />
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
          创建
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
            placeholder="请选择目标部门"
          />
        </el-form-item>
        <el-form-item label="共享原因">
          <el-input
            v-model="shareForm.reason"
            type="textarea"
            :rows="4"
            placeholder="说明本次共享目的"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="shareDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="shareSubmitting" @click="handleCreateShareRequest">
          提交
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar-select {
  width: 220px;
}

@media (max-width: 960px) {
  .toolbar-select {
    width: 100%;
  }
}
</style>
