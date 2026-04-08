<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchKnowledgeBases, fetchKnowledgeDocuments, fetchMyKnowledgeBaseShareRequests, fetchPendingKnowledgeBaseShareRequests } from '@/api/modules/knowledge'
import { fetchMyDepartmentJoinRequests, fetchPendingDepartmentJoinRequests } from '@/api/modules/organization'
import { useAuthStore } from '@/stores/auth'
import { formatMembershipLabel, getPreferredMembership } from '@/utils/organization'

const authStore = useAuthStore()

const loading = ref(false)
const knowledgeBaseCount = ref(0)
const documentCount = ref(0)
const pendingJoinCount = ref(0)
const pendingShareCount = ref(0)
const myJoinCount = ref(0)
const myShareCount = ref(0)

const memberships = computed(() => authStore.user?.memberships ?? [])
const currentMembership = computed(() => getPreferredMembership(memberships.value))
const pendingApprovalCount = computed(() => pendingJoinCount.value + pendingShareCount.value)
const myRequestCount = computed(() => myJoinCount.value + myShareCount.value)

const actionTiles = computed(() => [
  {
    title: '进入知识空间',
    description: '先从你当前可访问的空间开始浏览和治理资料。',
    to: '/knowledge-bases',
  },
  {
    title: '上传新文档',
    description: '上传入口已经独立出来，只做一件事。',
    to: '/documents/upload',
  },
  {
    title: '查看审批待办',
    description: pendingApprovalCount.value
      ? `你当前还有 ${pendingApprovalCount.value} 条待处理审批。`
      : '当前没有待处理审批，适合继续整理知识资产。',
    to: '/approvals',
  },
  {
    title: '开始知识检索',
    description: '在权限范围内直接搜索文档片段和知识来源。',
    to: '/knowledge/search',
  },
])

async function loadWorkspace() {
  loading.value = true
  try {
    const [
      knowledgeBaseResult,
      documentResult,
      pendingJoinResult,
      pendingShareResult,
      myJoinResult,
      myShareResult,
    ] = await Promise.allSettled([
      fetchKnowledgeBases(),
      fetchKnowledgeDocuments(),
      fetchPendingDepartmentJoinRequests(),
      fetchPendingKnowledgeBaseShareRequests(),
      fetchMyDepartmentJoinRequests(),
      fetchMyKnowledgeBaseShareRequests(),
    ])

    knowledgeBaseCount.value = knowledgeBaseResult.status === 'fulfilled' ? knowledgeBaseResult.value.count : 0
    documentCount.value = documentResult.status === 'fulfilled' ? documentResult.value.count : 0
    pendingJoinCount.value = pendingJoinResult.status === 'fulfilled' ? pendingJoinResult.value.count : 0
    pendingShareCount.value = pendingShareResult.status === 'fulfilled' ? pendingShareResult.value.count : 0
    myJoinCount.value = myJoinResult.status === 'fulfilled' ? myJoinResult.value.count : 0
    myShareCount.value = myShareResult.status === 'fulfilled' ? myShareResult.value.count : 0
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadWorkspace()
})
</script>

<template>
  <div class="page">
    <section class="hero-card workspace-hero">
      <div>
        <p class="page-eyebrow">Workspace</p>
        <h2>先从你自己的范围开始工作，而不是先理解整套治理体系。</h2>
        <p class="page-copy">
          当前工作部门、可访问空间、待处理审批和我的申请都已经收敛到这里。进入下一步时，你只需要按任务走，不需要自己拼产品地图。
        </p>
      </div>

      <div class="hero-card__summary">
        <span>{{ currentMembership?.department_name || '未设置' }}</span>
        <small>当前工作部门</small>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">工作部门</span>
        <strong>{{ currentMembership?.department_name || '--' }}</strong>
        <p>上传、浏览和协作都会优先以这个部门为默认上下文。</p>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可访问知识空间</span>
        <strong>{{ knowledgeBaseCount }}</strong>
        <p>当前组织归属和共享范围内可见的空间总数。</p>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">可访问文档</span>
        <strong>{{ documentCount }}</strong>
        <p>当前权限范围内已入库文档数量。</p>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">待处理审批</span>
        <strong>{{ pendingApprovalCount }}</strong>
        <p>包括加入部门审批和知识空间共享审批。</p>
      </el-card>
    </section>

    <section class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>下一步操作</template>
        <div class="action-grid">
          <router-link
            v-for="tile in actionTiles"
            :key="tile.title"
            class="action-tile"
            :to="tile.to"
          >
            <strong>{{ tile.title }}</strong>
            <span>{{ tile.description }}</span>
          </router-link>
        </div>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>我的组织范围</template>
        <el-skeleton :loading="loading" animated :rows="4">
          <template #default>
            <div class="roadmap-boxes">
              <div
                v-for="membership in memberships"
                :key="membership.id"
                class="roadmap-box"
              >
                <strong>{{ membership.department_name }}</strong>
                <span>{{ formatMembershipLabel(membership) }}</span>
              </div>
            </div>
          </template>
        </el-skeleton>
      </el-card>
    </section>

    <section class="grid-two">
      <el-card shadow="never" class="soft-card">
        <template #header>我发起的事项</template>
        <div class="roadmap-boxes">
          <div class="roadmap-box">
            <strong>{{ myRequestCount }} 条记录</strong>
            <span>包括加入部门申请和知识空间共享申请，方便你持续跟进结果。</span>
          </div>
          <div class="roadmap-box">
            <strong>{{ myJoinCount }} 条组织申请</strong>
            <span>协作部门申请会影响你的可见部门范围。</span>
          </div>
          <div class="roadmap-box">
            <strong>{{ myShareCount }} 条共享申请</strong>
            <span>共享一旦通过，目标部门会立即获得对应知识空间的访问资格。</span>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="soft-card">
        <template #header>使用节奏建议</template>
        <ul class="check-list">
          <li>先从知识空间进入，再决定上传到哪里，不要从“全局上传”开始。</li>
          <li>审批中心只看待办，不要在组织页里同时处理审批和治理。</li>
          <li>跨部门复用资料时，先共享空间，再让对方检索和查看。</li>
          <li>如果你有多个部门归属，先在顶部切到当前工作部门再继续操作。</li>
        </ul>
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.workspace-hero {
  align-items: center;
}
</style>
