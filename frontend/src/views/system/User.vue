<template>
  <div class="user-management">
    <div class="user-layout">
      <el-card class="department-panel" shadow="never">
        <template #header>
          <div class="panel-header">
            <div class="panel-title">
              <el-icon><OfficeBuilding /></el-icon>
              <span>部门树</span>
            </div>
            <el-button link type="primary" @click="handleSelectAllDepartments">全部部门</el-button>
          </div>
        </template>

        <el-input
          v-model="departmentKeyword"
          placeholder="请输入部门名称"
          clearable
          class="department-search"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-scrollbar class="department-tree-scroll">
          <el-tree
            ref="departmentTreeRef"
            :data="departmentTree"
            :props="{ label: 'name', children: 'children' }"
            node-key="id"
            default-expand-all
            highlight-current
            :expand-on-click-node="false"
            :filter-node-method="filterDepartmentNode"
            @node-click="handleDepartmentNodeClick"
          />
        </el-scrollbar>
      </el-card>

      <el-card class="user-table-panel" shadow="never">
        <template #header>
          <div class="card-header">
            <div class="card-header__title">
              <div class="card-title-main">
                <el-icon><UserFilled /></el-icon>
                <span>用户管理</span>
              </div>
              <el-tag v-if="selectedDepartmentName" type="primary" effect="plain">
                {{ selectedDepartmentName }}
              </el-tag>
            </div>

            <el-breadcrumb separator="/" class="user-breadcrumb">
              <el-breadcrumb-item>首页</el-breadcrumb-item>
              <el-breadcrumb-item>系统管理</el-breadcrumb-item>
              <el-breadcrumb-item>用户管理</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </template>

        <CrudToolbar>
          <template #search>
            <el-form :inline="true" :model="searchForm">
              <el-form-item>
                <el-input v-model="searchForm.username" placeholder="请输入用户名" clearable class="toolbar-input">
                  <template #prefix>
                    <el-icon><User /></el-icon>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item>
                <el-input v-model="searchForm.email" placeholder="请输入邮箱" clearable class="toolbar-input">
                  <template #prefix>
                    <el-icon><Message /></el-icon>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item>
                <CrudButton style-type="primary" tone="blue" :icon="Search" @click="handleSearch">搜索</CrudButton>
                <CrudButton style-type="secondary" tone="gray" :icon="Refresh" @click="handleReset">重置</CrudButton>
              </el-form-item>
            </el-form>
          </template>

          <template #actions>
            <CrudButton tone="blue" :icon="Plus" @click="handleAdd">新增</CrudButton>
            <CrudButton tone="green" :icon="EditPen" :disabled="selectedRows.length !== 1" @click="handleEditSelected">修改</CrudButton>
            <CrudButton tone="red" :icon="Delete" :disabled="selectedRows.length !== 1" @click="handleDeleteSelected">删除</CrudButton>
            <CrudButton tone="gray" :icon="Upload" @click="handleImport">导入</CrudButton>
            <CrudButton tone="amber" :icon="Download" @click="handleExport">导出</CrudButton>
          </template>
        </CrudToolbar>

        <CrudTable
          :data="tableData"
          :loading="loading"
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :total="pagination.total"
          :show-summary="true"
          :summary-icon="Files"
          :summary-text="`共 ${pagination.total} 条`"
          @update:current-page="pagination.page = $event"
          @update:page-size="pagination.pageSize = $event"
          @selection-change="handleSelectionChange"
          @page-size-change="handleSizeChange"
          @page-current-change="handleCurrentChange"
        >
          <el-table-column type="selection" width="54" align="center" />
          <el-table-column prop="id" label="用户编号" width="110" align="center" />
          <el-table-column prop="username" label="用户名" min-width="140" />
          <el-table-column prop="email" label="邮箱" min-width="220" />
          <el-table-column prop="departmentName" label="部门" min-width="160" show-overflow-tooltip />
          <el-table-column prop="roleNames" label="角色" min-width="160" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="120" align="center">
            <template #default="{ row }">
              <el-switch
                v-model="row.status"
                :active-value="1"
                :inactive-value="0"
                @change="handleStatusChange(row)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="创建时间" min-width="180" align="center" />
          <el-table-column label="操作" width="250" fixed="right" align="center">
            <template #default="{ row }">
              <div class="table-actions">
                <CrudButton style-type="primary" size-variant="table" tone="blue" :icon="UserFilled" @click="handleAssignRoles(row)">角色</CrudButton>
                <CrudButton style-type="primary" size-variant="table" tone="blue" :icon="Edit" @click="handleEdit(row)">编辑</CrudButton>
                <CrudButton style-type="primary" size-variant="table" tone="red" :icon="Delete" @click="handleDelete(row)">删除</CrudButton>
              </div>
            </template>
          </el-table-column>
        </CrudTable>
      </el-card>
    </div>

    <CrudFormDialog
      ref="formDialogRef"
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      :form-model="formData"
      :rules="rules"
      label-width="80px"
      :confirm-loading="submitLoading"
      @submit="handleSubmit"
      @close="handleDialogClose"
    >
      <el-form-item label="用户名" prop="username">
        <el-input v-model="formData.username" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="formData.email" placeholder="请输入邮箱" />
      </el-form-item>
      <el-form-item label="部门" prop="departmentId">
        <el-tree-select
          v-model="formData.departmentId"
          :data="departmentTreeOptions"
          :props="{ label: 'name', value: 'id' }"
          placeholder="请选择所属部门"
          check-strictly
          clearable
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item v-if="!formData.id" label="密码" prop="password">
        <el-input v-model="formData.password" type="password" placeholder="请输入密码" show-password />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formData.status">
          <el-radio :value="1">正常</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
    </CrudFormDialog>

    <el-dialog
      v-model="roleDialogVisible"
      :title="roleDialogTitle"
      width="520px"
      @close="handleRoleDialogClose"
    >
      <div v-loading="roleDialogLoading">
        <el-form label-width="80px">
          <el-form-item label="角色分配">
            <el-select
              v-model="selectedRoleIds"
              multiple
              clearable
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择角色"
              style="width: 100%"
            >
              <el-option
                v-for="role in roleOptions"
                :key="role.id"
                :label="role.name"
                :value="role.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="roleSubmitLoading" @click="handleRoleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Delete,
  Download,
  Edit,
  EditPen,
  Files,
  Message,
  OfficeBuilding,
  Plus,
  Refresh,
  Search,
  Upload,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import CrudButton from '../../components/crud/CrudButton.vue'
import CrudFormDialog from '../../components/crud/CrudFormDialog.vue'
import CrudTable from '../../components/crud/CrudTable.vue'
import CrudToolbar from '../../components/crud/CrudToolbar.vue'
import { getUserList, createUser, updateUser, deleteUser, getUserDetail, assignUserRoles } from '../../api/user'
import { getDepartmentList } from '../../api/department'
import { getRoleList } from '../../api/role'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增用户')
const formDialogRef = ref(null)
const departmentTreeRef = ref(null)
const departmentTree = ref([])
const departmentKeyword = ref('')
const selectedDepartmentId = ref(null)
const selectedDepartmentName = ref('')
const selectedRows = ref([])
const roleDialogVisible = ref(false)
const roleDialogTitle = ref('分配角色')
const roleDialogLoading = ref(false)
const roleSubmitLoading = ref(false)
const roleOptions = ref([])
const selectedRoleIds = ref([])
const currentRoleUserId = ref(null)

const searchForm = reactive({
  username: '',
  email: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const tableData = ref([])

const formData = reactive({
  id: null,
  username: '',
  email: '',
  departmentId: null,
  password: '',
  status: 1
})

const departmentTreeOptions = computed(() => departmentTree.value)

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
}

const findDepartmentName = (nodes, id) => {
  for (const node of nodes) {
    if (node.id === id) {
      return node.name
    }
    if (node.children?.length) {
      const childName = findDepartmentName(node.children, id)
      if (childName) {
        return childName
      }
    }
  }
  return ''
}

const filterDepartmentNode = (value, data) => {
  if (!value) return true
  return data.name?.includes(value)
}

watch(departmentKeyword, (value) => {
  departmentTreeRef.value?.filter(value)
})

const fetchUserList = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize,
      ...searchForm,
      ...(selectedDepartmentId.value ? { departmentId: selectedDepartmentId.value } : {})
    }
    const res = await getUserList(params)
    const users = res.data?.list || res.data || res.list || []
    tableData.value = users.map(user => ({
      ...user,
      departmentName: user.department?.name || '-',
      roleNames: user.roles?.map(item => item.role?.name).filter(Boolean).join('、') || '-'
    }))
    pagination.total = res.data?.total || res.total || tableData.value.length
  } catch (error) {
    ElMessage.error(error.message || '获取用户列表失败')
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

const fetchDepartmentTree = async () => {
  try {
    const res = await getDepartmentList()
    departmentTree.value = res.data || res.list || []
  } catch (error) {
    departmentTree.value = []
    ElMessage.error(error.message || '获取部门列表失败')
  }
}

const handleDepartmentNodeClick = (node) => {
  selectedDepartmentId.value = node.id
  selectedDepartmentName.value = node.name
  pagination.page = 1
  fetchUserList()
}

const handleSelectAllDepartments = () => {
  selectedDepartmentId.value = null
  selectedDepartmentName.value = ''
  departmentTreeRef.value?.setCurrentKey(null)
  pagination.page = 1
  fetchUserList()
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const handleSearch = () => {
  pagination.page = 1
  fetchUserList()
}

const handleReset = () => {
  searchForm.username = ''
  searchForm.email = ''
  handleSearch()
}

const handleAdd = () => {
  dialogTitle.value = '新增用户'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑用户'
  Object.assign(formData, {
    id: row.id,
    username: row.username,
    email: row.email || '',
    departmentId: row.departmentId || null,
    password: '',
    status: row.status ?? 1
  })
  dialogVisible.value = true
}

const handleEditSelected = () => {
  if (selectedRows.value.length === 1) {
    handleEdit(selectedRows.value[0])
  }
}

const fetchRoleOptions = async () => {
  const res = await getRoleList({ page: 1, pageSize: 1000 })
  roleOptions.value = res.data?.list || res.data || res.list || []
}

const extractUserRoleIds = (user) => {
  return (user?.roles || [])
    .map((item) => item.roleId ?? item.role?.id)
    .filter((id) => typeof id === 'number')
}

const handleAssignRoles = async (row) => {
  currentRoleUserId.value = row.id
  roleDialogTitle.value = `分配角色 - ${row.username}`
  roleDialogVisible.value = true
  roleDialogLoading.value = true

  try {
    const [roleRes, userRes] = await Promise.all([
      getRoleList({ page: 1, pageSize: 1000 }),
      getUserDetail(row.id)
    ])

    roleOptions.value = roleRes.data?.list || roleRes.data || roleRes.list || []
    const userDetail = userRes.data || userRes
    selectedRoleIds.value = extractUserRoleIds(userDetail)
  } catch (error) {
    ElMessage.error(error.message || '获取角色分配信息失败')
    roleDialogVisible.value = false
  } finally {
    roleDialogLoading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该用户吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    fetchUserList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleDeleteSelected = async () => {
  if (selectedRows.value.length === 1) {
    await handleDelete(selectedRows.value[0])
  }
}

const handleImport = () => {
  ElMessage.info('导入功能后续接入')
}

const handleExport = () => {
  ElMessage.info('导出功能后续接入')
}

const handleStatusChange = async (row) => {
  try {
    await updateUser(row.id, {
      username: row.username,
      email: row.email,
      departmentId: row.departmentId,
      status: row.status
    })
    ElMessage.success('状态更新成功')
  } catch (error) {
    row.status = row.status === 1 ? 0 : 1
    ElMessage.error(error.message || '状态更新失败')
  }
}

const handleRoleSubmit = async () => {
  if (!currentRoleUserId.value) return

  roleSubmitLoading.value = true
  try {
    await assignUserRoles(currentRoleUserId.value, selectedRoleIds.value)
    ElMessage.success('角色分配成功')
    roleDialogVisible.value = false
    await fetchUserList()
  } catch (error) {
    ElMessage.error(error.message || '角色分配失败')
  } finally {
    roleSubmitLoading.value = false
  }
}

const handleSubmit = async () => {
  if (!formDialogRef.value) return

  await formDialogRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        const payload = {
          username: formData.username,
          email: formData.email,
          ...(formData.departmentId ? { departmentId: formData.departmentId } : {}),
          status: formData.status
        }

        if (formData.id) {
          await updateUser(formData.id, payload)
          ElMessage.success('更新成功')
        } else {
          await createUser({
            ...payload,
            password: formData.password
          })
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchUserList()
      } catch (error) {
        ElMessage.error(error.message || '操作失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

const handleDialogClose = () => {
  formDialogRef.value?.resetFields()
  Object.assign(formData, {
    id: null,
    username: '',
    email: '',
    departmentId: selectedDepartmentId.value || null,
    password: '',
    status: 1
  })
}

const handleRoleDialogClose = () => {
  currentRoleUserId.value = null
  roleDialogTitle.value = '分配角色'
  selectedRoleIds.value = []
}

const handleSizeChange = () => {
  fetchUserList()
}

const handleCurrentChange = () => {
  fetchUserList()
}

onMounted(async () => {
  await fetchDepartmentTree()
  await fetchRoleOptions()
  if (selectedDepartmentId.value) {
    selectedDepartmentName.value = findDepartmentName(departmentTree.value, selectedDepartmentId.value)
  }
  fetchUserList()
})
</script>

<style scoped>
.user-management {
  padding: 0;
}

.user-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.department-panel,
.user-table-panel {
  border: none;
  border-radius: 20px;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.06);
}

.department-panel {
  min-height: 740px;
}

.panel-header,
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.panel-title,
.card-title-main {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1f2a37;
  font-weight: 700;
}

.card-header__title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-breadcrumb {
  color: #8a9aae;
}

.department-search {
  margin-bottom: 12px;
}

.department-tree-scroll {
  height: 642px;
}

.toolbar-input {
  width: 250px;
}

.table-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

@media (max-width: 960px) {
  .user-layout {
    grid-template-columns: 1fr;
  }

  .department-panel {
    min-height: auto;
  }

  .department-tree-scroll {
    height: 280px;
  }

  .toolbar-input {
    width: 100%;
  }
}
</style>
