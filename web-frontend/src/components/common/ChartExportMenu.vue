<template>
  <el-dropdown trigger="click" placement="bottom-end" @command="handleCommand">
    <el-button text size="small" :aria-label="'Export chart options'">
      <el-icon><Download /></el-icon>
      Export
    </el-button>
    
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="png" :aria-label="'Export as PNG image'">
          <el-icon><Picture /></el-icon>
          Export as PNG
        </el-dropdown-item>
        <el-dropdown-item command="jpg" :aria-label="'Export as JPG image'">
          <el-icon><Picture /></el-icon>
          Export as JPG
        </el-dropdown-item>
        <el-dropdown-item command="svg" :aria-label="'Export as SVG vector'">
          <el-icon><Document /></el-icon>
          Export as SVG
        </el-dropdown-item>
        <el-dropdown-item divided command="copy" :aria-label="'Copy to clipboard'">
          <el-icon><CopyDocument /></el-icon>
          Copy to Clipboard
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Picture, Document, CopyDocument } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

interface Props {
  chartInstance: echarts.ECharts | null
  chartTitle?: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'export-success': [format: string]
  'export-error': [error: string]
}>()

// Methods
const handleCommand = async (command: string) => {
  if (!props.chartInstance) {
    ElMessage.error('Chart not available for export')
    return
  }

  try {
    switch (command) {
      case 'png':
        await exportAsImage('png')
        break
      case 'jpg':
        await exportAsImage('jpeg')
        break
      case 'svg':
        await exportAsSVG()
        break
      case 'copy':
        await copyToClipboard()
        break
    }
  } catch (error) {
    console.error('Export failed:', error)
    emit('export-error', `Failed to export as ${command}`)
    ElMessage.error(`Failed to export as ${command}`)
  }
}

const exportAsImage = async (format: 'png' | 'jpeg') => {
  const dataURL = props.chartInstance!.getDataURL({
    type: format,
    pixelRatio: 2,
    backgroundColor: '#fff'
  })

  const link = document.createElement('a')
  link.download = `${props.chartTitle || 'chart'}_${new Date().toISOString().split('T')[0]}.${format}`
  link.href = dataURL
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  emit('export-success', format)
  ElMessage.success(`Chart exported as ${format.toUpperCase()}`)
}

const exportAsSVG = async () => {
  const svgData = props.chartInstance!.renderToSVGString()
  
  const blob = new Blob([svgData], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.download = `${props.chartTitle || 'chart'}_${new Date().toISOString().split('T')[0]}.svg`
  link.href = url
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
  
  emit('export-success', 'svg')
  ElMessage.success('Chart exported as SVG')
}

const copyToClipboard = async () => {
  try {
    const dataURL = props.chartInstance!.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })

    // Convert dataURL to blob
    const response = await fetch(dataURL)
    const blob = await response.blob()
    
    // Copy to clipboard
    await navigator.clipboard.write([
      new ClipboardItem({
        'image/png': blob
      })
    ])

    emit('export-success', 'clipboard')
    ElMessage.success('Chart copied to clipboard')
  } catch (error) {
    // Fallback for browsers that don't support clipboard API
    try {
      const dataURL = props.chartInstance!.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
      })

      const textarea = document.createElement('textarea')
      textarea.value = dataURL
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)

      emit('export-success', 'clipboard')
      ElMessage.success('Chart data copied to clipboard (fallback)')
    } catch (fallbackError) {
      throw new Error('Failed to copy to clipboard')
    }
  }
}
</script>

<style scoped>
/* Dropdown menu styles */
:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

:deep(.el-dropdown-menu__item:hover) {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}
</style>
