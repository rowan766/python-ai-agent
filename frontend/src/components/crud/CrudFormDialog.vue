<template>
  <el-dialog
    v-model="visibleProxy"
    :title="title"
    :width="width"
    :destroy-on-close="destroyOnClose"
    v-bind="dialogProps"
    @close="emit('close')"
    @closed="emit('closed')"
  >
    <el-form
      ref="formRef"
      :model="formModel"
      :rules="rules"
      :label-width="labelWidth"
      v-bind="formProps"
    >
      <slot />
    </el-form>

    <template #footer>
      <slot name="footer">
        <el-button @click="visibleProxy = false">{{ cancelText }}</el-button>
        <el-button type="primary" :loading="confirmLoading" @click="emit('submit')">{{ confirmText }}</el-button>
      </slot>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  width: {
    type: String,
    default: '600px'
  },
  formModel: {
    type: Object,
    required: true
  },
  rules: {
    type: Object,
    default: () => ({})
  },
  labelWidth: {
    type: String,
    default: '80px'
  },
  confirmLoading: {
    type: Boolean,
    default: false
  },
  confirmText: {
    type: String,
    default: '确定'
  },
  cancelText: {
    type: String,
    default: '取消'
  },
  destroyOnClose: {
    type: Boolean,
    default: false
  },
  dialogProps: {
    type: Object,
    default: () => ({})
  },
  formProps: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'submit', 'close', 'closed'])

const formRef = ref(null)

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const validate = async (callback) => formRef.value?.validate(callback)
const resetFields = () => formRef.value?.resetFields()
const clearValidate = (props) => formRef.value?.clearValidate(props)

defineExpose({
  formRef,
  validate,
  resetFields,
  clearValidate
})
</script>
