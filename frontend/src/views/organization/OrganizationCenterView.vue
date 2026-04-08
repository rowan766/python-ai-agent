<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import {
  createDepartmentJoinRequest,
  fetchDepartmentTree,
  fetchMyDepartmentJoinRequests,
} from '@/api/modules/organization'
import type { DepartmentJoinRequestItem, DepartmentNode } from '@/types/organization'
import { formatMembershipLabel, getPrimaryMembership } from '@/utils/organization'

const authStore = useAuthStore()

const loading = ref(false)
const submitting = ref(false)
const departments = ref<DepartmentNode[]>([])
const myRequests = ref<DepartmentJoinRequestItem[]>([])

const joinForm = reactive({
  target_department_id: undefined as number | undefined,
  reason: '',
})

const memberships = computed(() => authStore.user?.memberships ?? [])
const primaryMembership = computed(() => getPrimaryMembership(memberships.value))

async function loadData() {
  loading.value = true
  try {
    const [treeResult, requestResult] = await Promise.all([
      fetchDepartmentTree(),
      fetchMyDepartmentJoinRequests(),
    ])
    departments.value = treeResult.items
    myRequests.value = requestResult.items
    await authStore.fetchCurrentUser()
  } catch (error) {
    ElMessage.error('读取组织中心数据失败，请稍后重试。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleJoinRequest() {
  if (!joinForm.target_department_id) {
    ElMessage.warning('请先选择目标部门。')
    return
  }

  if (!joinForm.reason.trim()) {
    ElMessage.warning('请说明你为什么需要加入这个协作部门。')
    return
  }

  submitting.value = true
  try {
    await createDepartmentJoinRequest({
      target_department_id: joinForm.target_department_id,
      requested_role_code: 'department_member',
      reason: joinForm.reason.trim(),
    })
    ElMessage.success('协作部门申请已提交。')
    joinForm.reason = ''
    await loadData()
  } catch (error) {
    ElMessage.error('申请提交失败，请确认是否已有待处理记录。')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="page">
    <section class="hero-card organization-hero">
      <div>
        <p class="page-eyebrow">Organization</p>
        <h2>组织页面只负责一件事：让你看清自己和部门结构的关系。</h2>
        <p class="page-copy">
          知识空间、上传、审批都已经拆到独立页面。这里保留组织身份、部门结构和扩展协作部门申请，不再把多种流程塞进一个 tab。
        </p>
      </div>
      <div class="hero-card__summary">
        <span>{{ primaryMembership?.department_name || '未设置' }}</span>
        <small>{{ primaryMembership ? '当前主归属部门' : '请先完成组织接入' }}</small>
        <router-link class="hero-card__link" to="/departments">进入部门治理</router-link>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">归属部门数</span>
        <strong>{{ memberships.length }}</strong>
        <p>主归属与协作部门会共同影响你的可见范围。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">主归属部门</span>
        <strong>{{ primaryMembership?.department_name || '--' }}</strong>
        <p>这是创建知识空间和默认上传的首选部门。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">组织树规模</span>
        <strong>{{ departments.length }}</strong>
        <p>用于发起协作部门申请和浏览组织结构。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">我的申请记录</span>
        <strong>{{ myRequests.length }}</strong>
        <p>所有组织归属相关的申请都会沉淀在这里。</p>
      </el-card>
    </section>

    <section class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>我的组织身份</template>
        <el-skeleton :loading="loading" animated :rows="4">
          <template #default>
            <div class="roadmap-boxes">
              <div
                v-for="membership in memberships"
                :key="membership.id"
                class="roadmap-box"
              >
                <strong>{{ membership.department_name }}</strong>
                <span>{{ formatMembershipLabel(membership) }} · 影响你的知识空间、文档和审批范围</span>
              </div>
            </div>
          </template>
        </el-skeleton>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>申请新的协作部门</template>
        <el-form label-position="top">
          <el-form-item label="目标部门">
            <el-tree-select
              v-model="joinForm.target_department_id"
              :data="departments"
              node-key="id"
              check-strictly
              default-expand-all
              :props="{ label: 'name', children: 'children', value: 'id' }"
              placeholder="请选择你想加入的协作部门"
            />
          </el-form-item>
          <el-form-item label="协作原因">
            <el-input
              v-model="joinForm.reason"
              type="textarea"
              :rows="4"
              placeholder="例如：需要维护研发规范和产品复盘之间的跨部门知识流转"
            />
          </el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleJoinRequest">
            提交协作申请
          </el-button>
        </el-form>
      </el-card>
    </section>

    <section class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>部门结构</template>
        <el-tree
          :data="departments"
          node-key="id"
          default-expand-all
          :props="{ label: 'name', children: 'children' }"
          empty-text="暂无部门"
        />
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>组织申请记录</template>
        <el-table :data="myRequests" empty-text="还没有发起过协作申请">
          <el-table-column prop="target_department_name" label="目标部门" min-width="160" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="reason" label="申请原因" min-width="220" show-overflow-tooltip />
          <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
        </el-table>
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.organization-hero {
  align-items: center;
}

.hero-card__link {
  color: #1f6f54;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}
</style>
