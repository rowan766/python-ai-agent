<template>
  <div class="knowledge-space-page">
    <el-card class="knowledge-space-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <el-icon><Collection /></el-icon>
            <span>知识空间</span>
          </div>
          <el-button v-permission="'knowledge:space:create'" type="primary" :icon="Plus" @click="handleCreate">
            创建空间
          </el-button>
        </div>
      </template>

      <div class="toolbar">
        <el-form :inline="true" :model="searchForm">
          <el-form-item>
            <el-input v-model="searchForm.keyword" placeholder="请输入空间名称" clearable class="toolbar-input">
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-select v-model="searchForm.status" clearable placeholder="空间状态" class="toolbar-select">
              <el-option label="启用" :value="1" />
              <el-option label="停用" :value="0" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table
        :data="tableData"
        border
        class="space-table"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="name" label="空间名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="description" label="空间描述" min-width="240" show-overflow-tooltip />
        <el-table-column label="归属部门" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.ownerDepartment?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="可见性" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getVisibilityTagType(row.visibilityMode)" effect="light">
              {{ getVisibilityText(row.visibilityMode) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="light">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="memberCount" label="成员数" width="90" align="center" />
        <el-table-column prop="shareCount" label="共享数" width="90" align="center" />
        <el-table-column prop="updatedAt" label="更新时间" min-width="170" align="center" />
        <el-table-column label="操作" width="300" fixed="right" align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
              <el-button link type="primary" @click="handleOpenDetail(row)">详情</el-button>
              <el-button v-permission="'knowledge:space:share'" link type="warning" @click="handleManage(row)">成员共享</el-button>
              <el-button
                v-if="(row.status === 0 || row.createdBy === userStore.userInfo?.id) && (row.documentCount ?? 0) === 0"
                link
                type="danger"
                @click="handleDeleteSpace(row)"
              >删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next, sizes"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="formDialogVisible"
      :title="formDialogTitle"
      width="720px"
      @close="handleFormDialogClose"
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="空间名称" prop="name">
              <el-input v-model="formData.name" placeholder="请输入空间名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="归属部门" prop="ownerDepartmentId">
              <el-tree-select
                v-model="formData.ownerDepartmentId"
                :data="departmentOptions"
                :props="{ label: 'name', value: 'id' }"
                check-strictly
                clearable
                placeholder="请选择归属部门"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="可见性" prop="visibilityMode">
              <el-select v-model="formData.visibilityMode" style="width: 100%">
                <el-option label="仅知识空间成员可见" value="private" />
                <el-option label="同部门可见" value="department" />
                <el-option label="同部门及下属部门可见" value="department_tree" />
                <el-option label="按共享可见" value="shared" />
                <el-option label="全体成员可见" value="all" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="formData.status">
                <el-radio :value="1">启用</el-radio>
                <el-radio :value="0">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="空间描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="4"
            maxlength="500"
            placeholder="请输入空间描述"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmitForm">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="detailDrawerVisible"
      title="知识空间详情"
      size="62%"
      @close="handleDetailDrawerClose"
    >
      <div v-loading="detailLoading" class="detail-drawer">
        <el-descriptions v-if="activeSpaceDetail" :column="2" border>
          <el-descriptions-item label="空间名称">{{ activeSpaceDetail.name }}</el-descriptions-item>
          <el-descriptions-item label="归属部门">{{ activeSpaceDetail.ownerDepartment?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ activeSpaceDetail.creator?.nickname || activeSpaceDetail.creator?.username || '-' }}</el-descriptions-item>
          <el-descriptions-item label="可见性">{{ getVisibilityText(activeSpaceDetail.visibilityMode) }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ activeSpaceDetail.status === 1 ? '启用' : '停用' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ activeSpaceDetail.updatedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ activeSpaceDetail.description || '暂无' }}</el-descriptions-item>
        </el-descriptions>

        <el-tabs v-if="activeSpaceDetail" class="detail-tabs">
          <el-tab-pane label="成员">
            <el-table :data="activeSpaceDetail.members || []" border>
              <el-table-column prop="user.username" label="用户名" min-width="140" />
              <el-table-column label="昵称" min-width="140">
                <template #default="{ row }">
                  {{ row.user?.nickname || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="spaceRole" label="空间角色" width="120" align="center" />
              <el-table-column prop="updatedAt" label="更新时间" min-width="160" align="center" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="共享">
            <el-table :data="activeSpaceDetail.shares || []" border>
              <el-table-column label="目标类型" width="120" align="center">
                <template #default="{ row }">
                  {{ getTargetTypeText(row.targetType) }}
                </template>
              </el-table-column>
              <el-table-column label="目标名称" min-width="180">
                <template #default="{ row }">
                  {{ getShareTargetLabel(row) }}
                </template>
              </el-table-column>
              <el-table-column prop="permissionLevel" label="权限级别" width="120" align="center" />
              <el-table-column prop="updatedAt" label="更新时间" min-width="160" align="center" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>

    <el-drawer
      v-model="manageDrawerVisible"
      title="成员与共享配置"
      size="72%"
      @close="handleManageDrawerClose"
    >
      <div v-loading="detailLoading" class="manage-drawer">
        <div v-if="activeSpaceDetail" class="manage-header">
          <div>
            <h3>{{ activeSpaceDetail.name }}</h3>
            <p>{{ activeSpaceDetail.description || '这个空间还没有填写描述。' }}</p>
          </div>
        </div>

        <el-tabs v-if="activeSpaceDetail" class="manage-tabs">
          <el-tab-pane label="成员管理">
            <div class="inline-form">
              <el-select v-model="memberForm.userId" filterable placeholder="请选择用户" class="inline-field">
                <el-option
                  v-for="user in userOptions"
                  :key="user.id"
                  :label="user.label"
                  :value="user.id"
                />
              </el-select>
              <el-select v-model="memberForm.spaceRole" placeholder="请选择角色" class="inline-field">
                <el-option label="Owner" value="owner" />
                <el-option label="Manager" value="manager" />
                <el-option label="Editor" value="editor" />
                <el-option label="Viewer" value="viewer" />
              </el-select>
              <el-button type="primary" :loading="memberSubmitting" @click="handleSaveMember">保存成员</el-button>
            </div>

            <el-table :data="activeSpaceDetail.members || []" border>
              <el-table-column label="用户名" min-width="140">
                <template #default="{ row }">
                  {{ row.user?.username || `用户#${row.userId}` }}
                </template>
              </el-table-column>
              <el-table-column label="昵称" min-width="140">
                <template #default="{ row }">
                  {{ row.user?.nickname || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="spaceRole" label="空间角色" width="120" align="center" />
              <el-table-column label="操作" width="100" align="center">
                <template #default="{ row }">
                  <el-button link type="danger" @click="handleDeleteMember(row)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="共享配置">
            <div class="inline-form">
              <el-select v-model="shareForm.targetType" placeholder="共享目标类型" class="inline-field" @change="handleShareTargetTypeChange">
                <el-option label="用户" value="user" />
                <el-option label="角色" value="role" />
                <el-option label="部门" value="department" />
              </el-select>
              <el-select v-model="shareForm.targetId" filterable placeholder="请选择共享目标" class="inline-field">
                <el-option
                  v-for="item in currentShareTargetOptions"
                  :key="`${shareForm.targetType}-${item.id}`"
                  :label="item.label"
                  :value="item.id"
                />
              </el-select>
              <el-select v-model="shareForm.permissionLevel" placeholder="权限级别" class="inline-field">
                <el-option label="只读" value="read" />
                <el-option label="写入" value="write" />
                <el-option label="管理" value="manage" />
                <el-option label="共享" value="share" />
              </el-select>
              <el-button type="primary" :loading="shareSubmitting" @click="handleSaveShare">保存共享</el-button>
            </div>

            <el-table :data="activeSpaceDetail.shares || []" border>
              <el-table-column label="目标类型" width="120" align="center">
                <template #default="{ row }">
                  {{ getTargetTypeText(row.targetType) }}
                </template>
              </el-table-column>
              <el-table-column label="目标名称" min-width="180">
                <template #default="{ row }">
                  {{ getShareTargetLabel(row) }}
                </template>
              </el-table-column>
              <el-table-column prop="permissionLevel" label="权限级别" width="120" align="center" />
              <el-table-column label="操作" width="100" align="center">
                <template #default="{ row }">
                  <el-button link type="danger" @click="handleDeleteShare(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, Plus, Search } from '@element-plus/icons-vue'
import { useUserStore } from '../../stores/user'
import { getDepartmentList } from '../../api/department'
import {
  createKnowledgeSpace,
  deleteKnowledgeSpace,
  deleteKnowledgeSpaceMember,
  deleteKnowledgeSpaceShare,
  getKnowledgeSpaceDetail,
  getKnowledgeSpaceList,
  saveKnowledgeSpaceMember,
  saveKnowledgeSpaceShare,
  updateKnowledgeSpace,
} from '../../api/knowledge-space'
import { getRoleList } from '../../api/role'
import { getUserList } from '../../api/user'

const userStore = useUserStore()
const loading = ref(false)
const detailLoading = ref(false)
const submitLoading = ref(false)
const memberSubmitting = ref(false)
const shareSubmitting = ref(false)
const formDialogVisible = ref(false)
const formDialogTitle = ref('创建知识空间')
const detailDrawerVisible = ref(false)
const manageDrawerVisible = ref(false)
const formRef = ref(null)

const tableData = ref([])
const activeSpaceDetail = ref(null)
const departmentOptions = ref([])
const roleOptions = ref([])
const userOptions = ref([])

const searchForm = reactive({
  keyword: '',
  status: undefined,
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
})

const formData = reactive({
  id: null,
  name: '',
  description: '',
  ownerDepartmentId: null,
  visibilityMode: 'private',
  status: 1,
})

const memberForm = reactive({
  userId: null,
  spaceRole: 'viewer',
})

const shareForm = reactive({
  targetType: 'user',
  targetId: null,
  permissionLevel: 'read',
})

const formRules = {
  name: [
    { required: true, message: '请输入空间名称', trigger: 'blur' },
    { max: 100, message: '空间名称不能超过100个字符', trigger: 'blur' },
  ],
}

const currentShareTargetOptions = computed(() => {
  if (shareForm.targetType === 'department') return departmentOptions.value.map(item => ({ id: item.id, label: item.name }))
  if (shareForm.targetType === 'role') return roleOptions.value
  return userOptions.value
})

const flattenDepartmentTree = (nodes = [], acc = []) => {
  nodes.forEach((node) => {
    acc.push({ id: node.id, name: node.name })
    flattenDepartmentTree(node.children || [], acc)
  })
  return acc
}

const normalizePagedList = (response) => {
  const payload = response?.data ?? response ?? {}
  return {
    list: payload.list || [],
    total: payload.total || 0,
  }
}

const getVisibilityText = (mode) => {
  const map = {
    private: '仅知识空间成员可见',
    department: '同部门可见',
    department_tree: '同部门及下属部门可见',
    shared: '按共享可见',
    all: '全体成员可见',
  }
  return map[mode] || mode || '-'
}

const getVisibilityTagType = (mode) => {
  const map = {
    private: 'info',
    department: 'success',
    department_tree: 'success',
    shared: 'warning',
    all: 'primary',
  }
  return map[mode] || 'info'
}

const getTargetTypeText = (type) => {
  const map = {
    user: '用户',
    role: '角色',
    department: '部门',
  }
  return map[type] || type || '-'
}

const getShareTargetLabel = (share) => {
  if (!share) return '-'
  if (share.targetType === 'department') {
    return flattenDepartmentTree(departmentOptions.value).find(item => item.id === share.targetId)?.name || `部门#${share.targetId}`
  }
  if (share.targetType === 'role') {
    return roleOptions.value.find(item => item.id === share.targetId)?.label || `角色#${share.targetId}`
  }
  return userOptions.value.find(item => item.id === share.targetId)?.label || `用户#${share.targetId}`
}

const resetFormData = () => {
  Object.assign(formData, {
    id: null,
    name: '',
    description: '',
    ownerDepartmentId: null,
    visibilityMode: 'private',
    status: 1,
  })
}

const resetMemberForm = () => {
  memberForm.userId = null
  memberForm.spaceRole = 'viewer'
}

const resetShareForm = () => {
  shareForm.targetType = 'user'
  shareForm.targetId = null
  shareForm.permissionLevel = 'read'
}

const fetchSpaceList = async () => {
  loading.value = true
  try {
    const response = await getKnowledgeSpaceList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
      status: searchForm.status,
    })
    const { list, total } = normalizePagedList(response)
    tableData.value = list
    pagination.total = total
  } finally {
    loading.value = false
  }
}

const fetchDetail = async (id) => {
  detailLoading.value = true
  try {
    const response = await getKnowledgeSpaceDetail(id)
    activeSpaceDetail.value = response?.data ?? response ?? null
  } finally {
    detailLoading.value = false
  }
}

const fetchSupportOptions = async () => {
  const [departmentRes, roleRes, userRes] = await Promise.all([
    getDepartmentList(),
    getRoleList({ page: 1, pageSize: 1000 }),
    getUserList({ page: 1, pageSize: 1000 }),
  ])
  departmentOptions.value = departmentRes?.data || departmentRes || []
  const roleList = roleRes?.data?.list || roleRes?.list || []
  roleOptions.value = roleList.map(item => ({ id: item.id, label: item.name }))
  const userList = userRes?.data?.list || userRes?.list || []
  userOptions.value = userList.map(item => ({
    id: item.id,
    label: item.nickname ? `${item.username} (${item.nickname})` : item.username,
  }))
}

const handleSearch = () => {
  pagination.page = 1
  fetchSpaceList()
}

const handleReset = () => {
  searchForm.keyword = ''
  searchForm.status = undefined
  handleSearch()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchSpaceList()
}

const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchSpaceList()
}

const handleCreate = () => {
  resetFormData()
  formDialogTitle.value = '创建知识空间'
  formDialogVisible.value = true
}

const handleEdit = (row) => {
  Object.assign(formData, {
    id: row.id,
    name: row.name,
    description: row.description || '',
    ownerDepartmentId: row.ownerDepartmentId || null,
    visibilityMode: row.visibilityMode || 'private',
    status: row.status ?? 1,
  })
  formDialogTitle.value = '编辑知识空间'
  formDialogVisible.value = true
}

const handleSubmitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitLoading.value = true
    try {
      const payload = {
        name: formData.name,
        description: formData.description || undefined,
        ownerDepartmentId: formData.ownerDepartmentId || undefined,
        visibilityMode: formData.visibilityMode,
        status: formData.status,
      }

      if (formData.id) {
        await updateKnowledgeSpace(formData.id, payload)
        ElMessage.success('知识空间已更新')
      } else {
        await createKnowledgeSpace(payload)
        ElMessage.success('知识空间已创建')
      }
      formDialogVisible.value = false
      await fetchSpaceList()
    } finally {
      submitLoading.value = false
    }
  })
}

const handleFormDialogClose = () => {
  formRef.value?.resetFields()
  resetFormData()
}

const handleOpenDetail = async (row) => {
  detailDrawerVisible.value = true
  await fetchDetail(row.id)
}

const handleManage = async (row) => {
  manageDrawerVisible.value = true
  resetMemberForm()
  resetShareForm()
  await fetchDetail(row.id)
}

const handleDetailDrawerClose = () => {
  activeSpaceDetail.value = null
}

const handleManageDrawerClose = () => {
  activeSpaceDetail.value = null
  resetMemberForm()
  resetShareForm()
}

const handleSaveMember = async () => {
  if (!activeSpaceDetail.value?.id) return
  if (!memberForm.userId) {
    ElMessage.warning('请选择用户')
    return
  }

  memberSubmitting.value = true
  try {
    await saveKnowledgeSpaceMember(activeSpaceDetail.value.id, {
      userId: memberForm.userId,
      spaceRole: memberForm.spaceRole,
    })
    ElMessage.success('成员已保存')
    resetMemberForm()
    await fetchDetail(activeSpaceDetail.value.id)
    await fetchSpaceList()
  } finally {
    memberSubmitting.value = false
  }
}

const handleDeleteMember = async (row) => {
  if (!activeSpaceDetail.value?.id) return
  try {
    await ElMessageBox.confirm('确定移除该成员吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  await deleteKnowledgeSpaceMember(activeSpaceDetail.value.id, row.id)
  ElMessage.success('成员已移除')
  await fetchDetail(activeSpaceDetail.value.id)
  await fetchSpaceList()
}

const handleShareTargetTypeChange = () => {
  shareForm.targetId = null
}

const handleSaveShare = async () => {
  if (!activeSpaceDetail.value?.id) return
  if (!shareForm.targetId) {
    ElMessage.warning('请选择共享目标')
    return
  }

  shareSubmitting.value = true
  try {
    await saveKnowledgeSpaceShare(activeSpaceDetail.value.id, {
      targetType: shareForm.targetType,
      targetId: shareForm.targetId,
      permissionLevel: shareForm.permissionLevel,
    })
    ElMessage.success('共享配置已保存')
    resetShareForm()
    await fetchDetail(activeSpaceDetail.value.id)
    await fetchSpaceList()
  } finally {
    shareSubmitting.value = false
  }
}

const handleDeleteShare = async (row) => {
  if (!activeSpaceDetail.value?.id) return
  try {
    await ElMessageBox.confirm('确定删除这条共享配置吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  await deleteKnowledgeSpaceShare(activeSpaceDetail.value.id, row.id)
  ElMessage.success('共享配置已删除')
  await fetchDetail(activeSpaceDetail.value.id)
  await fetchSpaceList()
}

const handleDeleteSpace = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除知识空间「${row.name}」吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch {
    return
  }
  await deleteKnowledgeSpace(row.id)
  ElMessage.success('知识空间已删除')
  await fetchSpaceList()
}

onMounted(async () => {
  await fetchSupportOptions()
  await fetchSpaceList()
})
</script>

<style scoped>
.knowledge-space-page {
  padding: 0;
}

.knowledge-space-card {
  border: none;
  border-radius: 20px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.06);
}

.card-header,
.card-title,
.toolbar,
.table-actions,
.inline-form,
.manage-header {
  display: flex;
}

.card-header,
.manage-header {
  justify-content: space-between;
  align-items: center;
}

.card-title {
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #1f2937;
}

.toolbar {
  margin-bottom: 16px;
}

.toolbar-input {
  width: 260px;
}

.toolbar-select,
.inline-field {
  width: 180px;
}

.space-table {
  border: 1px solid #edf2f7;
  border-radius: 16px;
  overflow: hidden;
}

.table-actions {
  justify-content: center;
  gap: 12px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-drawer,
.manage-drawer {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.manage-header h3 {
  margin: 0 0 6px;
  color: #1f2937;
}

.manage-header p {
  margin: 0;
  color: #64748b;
}

.inline-form {
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

@media (max-width: 900px) {
  .toolbar,
  .inline-form {
    display: block;
  }

  .toolbar-input,
  .toolbar-select,
  .inline-field {
    width: 100%;
  }
}
</style>
