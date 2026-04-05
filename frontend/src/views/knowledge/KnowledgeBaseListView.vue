<script setup lang="ts">
import type { AxiosError } from 'axios'
import {
  createKnowledgeBase,
  createKnowledgeBaseShareRequest,
  fetchKnowledgeBaseShares,
  fetchKnowledgeBases,
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
import { computed, onMounted, reactive, ref } from 'vue'

const authStore = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const shareDialogVisible = ref(false)
const shareSubmitting = ref(false)
const knowledgeBases = ref<KnowledgeBaseItem[]>([])
const departmentTree = ref<DepartmentNode[]>([])
const shareMap = ref<Record<number, KnowledgeBaseShareItem[]>>({})
const selectedKnowledgeBaseForShare = ref<KnowledgeBaseItem | null>(null)

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
  { label: '部门私有', value: 'department_private' },
  { label: '部门共享', value: 'department_shared' },
  { label: '全组织公开', value: 'org_public' },
]

const membershipOptions = computed(() => authStore.user?.memberships ?? [])
const primaryMembership = computed(
  () => membershipOptions.value.find((item) => item.is_primary) ?? membershipOptions.value[0],
)

async function loadKnowledgeBases() {
  loading.value = true
  try {
    const [knowledgeBaseResult, departmentTreeResult] = await Promise.all([
      fetchKnowledgeBases(),
      fetchDepartmentTree(),
    ])
    knowledgeBases.value = knowledgeBaseResult.items
    departmentTree.value = departmentTreeResult.items
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
    console.error(error)
    ElMessage.error('读取知识库空间失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  if (primaryMembership.value && !createForm.department_id) {
    createForm.department_id = primaryMembership.value.department_id
  }
  dialogVisible.value = true
}

function openShareDialog(item: KnowledgeBaseItem) {
  selectedKnowledgeBaseForShare.value = item
  shareForm.target_department_id = undefined
  shareForm.reason = ''
  shareDialogVisible.value = true
}

async function handleCreateKnowledgeBase() {
  if (!createForm.department_id) {
    ElMessage.warning('请先选择归属部门。')
    return
  }
  if (!createForm.name.trim()) {
    ElMessage.warning('请输入知识库名称。')
    return
  }
  if (!createForm.code.trim()) {
    ElMessage.warning('请输入知识库编码。')
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
    ElMessage.success('知识库空间创建成功。')
    dialogVisible.value = false
    createForm.code = ''
    createForm.name = ''
    createForm.description = ''
    createForm.visibility_scope = 'department_private'
    await loadKnowledgeBases()
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '创建知识库空间失败。')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

async function handleCreateShareRequest() {
  if (!selectedKnowledgeBaseForShare.value) {
    return
  }
  if (!shareForm.target_department_id) {
    ElMessage.warning('请选择目标部门。')
    return
  }
  if (!shareForm.reason.trim()) {
    ElMessage.warning('请输入共享申请理由。')
    return
  }

  shareSubmitting.value = true
  try {
    await createKnowledgeBaseShareRequest(selectedKnowledgeBaseForShare.value.id, {
      target_department_id: shareForm.target_department_id,
      reason: shareForm.reason.trim(),
    })
    ElMessage.success('知识库共享申请已提交。')
    shareDialogVisible.value = false
  } catch (error) {
    const axiosError = error as AxiosError<{ detail?: string }>
    ElMessage.error(axiosError.response?.data?.detail || '提交共享申请失败。')
    console.error(error)
  } finally {
    shareSubmitting.value = false
  }
}

onMounted(async () => {
  await loadKnowledgeBases()
})
</script>

<template>
  <div class="page">
    <section class="hero-card">
      <div>
        <p class="page-eyebrow">Knowledge Bases</p>
        <h2>把知识治理正式落到“空间”上，而不是让所有文档散落在一个全局向量库里。</h2>
        <p class="page-copy">
          这一步已经接上真实接口。当前用户看到的，是自己所属部门或管理范围内可访问的知识库空间；文档上传和检索都会以这些空间作为归属边界。
        </p>
      </div>
      <div class="hero-card__summary">
        <span>{{ knowledgeBases.length }}</span>
        <small>当前可访问空间数</small>
        <el-button
          type="primary"
          :disabled="!membershipOptions.length"
          @click="openCreateDialog"
        >
          新建知识库
        </el-button>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可访问知识库</span>
        <strong>{{ knowledgeBases.length }}</strong>
        <p>按组织归属和管理范围过滤，不再是全员共享的单一入口。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">归属部门</span>
        <strong>{{ authStore.user?.memberships.length || 0 }}</strong>
        <p>当前登录用户的有效成员关系数量，会影响可见空间范围。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">默认上传入口</span>
        <strong>归属型</strong>
        <p>上传文档时必须先选知识库空间，便于权限、审计和检索隔离。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可见策略</span>
        <strong>可扩展</strong>
        <p>目前支持部门私有、部门共享和组织公开，后续可继续细化。</p>
      </el-card>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>空间清单</template>

      <el-skeleton :rows="4" animated v-if="loading" />

      <el-empty
        v-else-if="!knowledgeBases.length"
        description="当前还没有可访问的知识库空间。若你是部门负责人，可先创建首个空间。"
      />

      <div v-else class="kb-grid">
        <article v-for="item in knowledgeBases" :key="item.id" class="kb-card">
          <div class="kb-card__top">
            <div>
              <strong>{{ item.name }}</strong>
              <p>{{ item.description || '当前空间还没有补充描述。' }}</p>
            </div>
            <el-tag round>{{ item.visibility_scope }}</el-tag>
          </div>

          <div class="kb-card__meta">
            <span>归属部门：{{ item.department_name }}</span>
            <span>编码：{{ item.code }}</span>
            <span>文档数：{{ item.document_count }}</span>
          </div>

          <div class="kb-card__share">
            <div class="kb-card__share-head">
              <span>已共享给：</span>
              <el-button link type="primary" @click="openShareDialog(item)">发起共享</el-button>
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
    </el-card>

    <el-dialog v-model="dialogVisible" title="新建知识库空间" width="520px">
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
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreateKnowledgeBase">
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
        <el-button type="primary" :loading="shareSubmitting" @click="handleCreateShareRequest">
          提交共享申请
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
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
</style>
