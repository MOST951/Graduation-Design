<template>
  <div class="data-table-container">
    <!-- Skip to table link for accessibility -->
    <a href="#table-content" class="skip-link">Skip to table content</a>
    
    <!-- Table header with controls -->
    <div class="table-header">
      <div class="table-header-left">
        <h2 class="table-title">{{ title }}</h2>
        <p v-if="description" class="table-description">{{ description }}</p>
      </div>
      
      <div class="table-controls">
        <div class="search-container">
          <el-input
            v-model="searchQuery"
            :placeholder="searchPlaceholder"
            :aria-label="searchPlaceholder"
            clearable
            class="search-input"
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        
        <div class="filter-container">
          <el-select
            v-model="selectedFilter"
            :placeholder="filterPlaceholder"
            :aria-label="filterPlaceholder"
            class="filter-select"
            @change="handleFilter"
          >
            <el-option
              v-for="option in filterOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>
        
        <el-button
          type="primary"
          :aria-label="exportButtonLabel"
          :loading="isExporting"
          class="export-button"
          @click="handleExport"
        >
          <el-icon><Download /></el-icon>
          Export
        </el-button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="table-loading">
      <SkeletonLoader variant="table" :rows="5" :columns="columns.length" />
      <div class="loading-overlay" aria-live="polite" aria-atomic="true">
        Loading data...
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="table-error" role="alert">
      <el-alert
        :title="error.userMessage || 'Error loading data'"
        type="error"
        :description="error.action || 'Please try again later'"
        show-icon
        :closable="false"
      />
      <el-button class="retry-button" @click="handleRetry">
        <el-icon><Refresh /></el-icon>
        Retry
      </el-button>
    </div>

    <!-- Empty state -->
    <div v-else-if="filteredData.length === 0" class="table-empty" role="status">
      <div class="empty-content">
        <el-icon class="empty-icon"><Document /></el-icon>
        <h3 class="empty-title">{{ emptyTitle }}</h3>
        <p class="empty-description">{{ emptyDescription }}</p>
        <el-button v-if="showRefreshButton" type="primary" @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          Refresh
        </el-button>
      </div>
    </div>

    <!-- Table content -->
    <div v-else class="table-wrapper">
      <div class="table-info" aria-live="polite">
        Showing {{ startIndex }}-{{ endIndex }} of {{ totalItems }} items
      </div>
      
      <el-table
        id="table-content"
        :data="paginatedData"
        :row-key="rowKey"
        :default-sort="defaultSort"
        class="data-table"
        :aria-label="`${title} table with ${paginatedData.length} rows`"
        role="table"
        @sort-change="handleSortChange"
        @selection-change="handleSelectionChange"
      >
        <!-- Selection column -->
        <el-table-column
          v-if="selectable"
          type="selection"
          width="55"
          :selectable="isRowSelectable"
          aria-label="Select row"
        />

        <!-- Data columns -->
        <el-table-column
          v-for="column in visibleColumns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :width="column.width"
          :min-width="column.minWidth"
          :sortable="column.sortable"
          :formatter="column.formatter"
          :class-name="column.className"
          :aria-label="`${column.label} column`"
        >
          <template #default="{ row, $index }">
            <div class="table-cell-content">
              <!-- Custom cell content -->
              <slot
                :name="`cell-${column.prop}`"
                :row="row"
                :column="column"
                :index="$index"
              >
                <!-- Default cell rendering -->
                <span v-if="column.type === 'date'">
                  {{ formatDate(row[column.prop]) }}
                </span>
                <span v-else-if="column.type === 'number'">
                  {{ formatNumber(row[column.prop]) }}
                </span>
                <span v-else-if="column.type === 'status'">
                  <el-tag
                    :type="getStatusType(row[column.prop])"
                    size="small"
                    :aria-label="`Status: ${row[column.prop]}`"
                  >
                    {{ row[column.prop] }}
                  </el-tag>
                </span>
                <span v-else>
                  {{ row[column.prop] }}
                </span>
              </slot>
            </div>
          </template>
        </el-table-column>

        <!-- Action column -->
        <el-table-column
          v-if="hasActions"
          label="Actions"
          width="120"
          fixed="right"
          aria-label="Actions column"
        >
          <template #default="{ row, $index }">
            <div class="table-actions">
              <el-button
                v-for="action in getRowActions(row)"
                :key="action.key"
                :type="action.type"
                size="small"
                :aria-label="action.ariaLabel"
                class="action-button"
                @click="action.handler(row, $index)"
              >
                <el-icon v-if="action.icon">
                  <component :is="action.icon" />
                </el-icon>
                {{ action.label }}
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalItems"
          layout="total, sizes, prev, pager, next, jumper"
          :aria-label="`${title} pagination`"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- Selection info -->
    <div v-if="selectedRows.length > 0" class="selection-info" role="status">
      <span class="selection-count">
        {{ selectedRows.length }} items selected
      </span>
      <div class="selection-actions">
        <el-button
          v-for="action in selectionActions"
          :key="action.key"
          :type="action.type"
          size="small"
          :aria-label="action.ariaLabel"
          @click="action.handler(selectedRows)"
        >
          <el-icon v-if="action.icon">
            <component :is="action.icon" />
          </el-icon>
          {{ action.label }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Download, Document, Refresh } from '@element-plus/icons-vue'
import SkeletonLoader from './SkeletonLoader.vue'
import { withErrorHandling } from '@/utils/errorHandler'
import { AccessibilityHelper } from '@/utils/accessibility'

// Types
interface TableColumn {
  prop: string
  label: string
  width?: number
  minWidth?: number
  sortable?: boolean
  formatter?: (row: any, column: any, value: any, index: number) => string
  className?: string
  type?: 'text' | 'date' | 'number' | 'status'
  visible?: boolean
}

interface TableAction {
  key: string
  label: string
  type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  icon?: any
  handler: (row: any, index: number) => void
  ariaLabel: string
  condition?: (row: any) => boolean
}

interface FilterOption {
  value: string
  label: string
}

interface Props {
  title: string
  description?: string
  data: any[]
  columns: TableColumn[]
  loading?: boolean
  error?: any
  selectable?: boolean
  rowKey?: string
  defaultSort?: { prop: string; order: 'ascending' | 'descending' }
  searchPlaceholder?: string
  filterPlaceholder?: string
  filterOptions?: FilterOption[]
  actions?: TableAction[]
  selectionActions?: TableAction[]
  emptyTitle?: string
  emptyDescription?: string
  showRefreshButton?: boolean
  pageSize?: number
  dateFormat?: string
  numberFormat?: string
}

const props = withDefaults(defineProps<Props>(), {
  description: '',
  loading: false,
  error: null,
  selectable: false,
  rowKey: 'id',
  defaultSort: () => ({ prop: '', order: 'ascending' }),
  searchPlaceholder: 'Search...',
  filterPlaceholder: 'Filter...',
  filterOptions: () => [],
  actions: () => [],
  selectionActions: () => [],
  emptyTitle: 'No data available',
  emptyDescription: 'There are no items to display',
  showRefreshButton: true,
  pageSize: 20,
  dateFormat: 'YYYY-MM-DD',
  numberFormat: 'en-US'
})

// Emits
const emit = defineEmits<{
  search: [query: string]
  filter: [filter: string]
  sort: [sort: { prop: string; order: 'ascending' | 'descending' }]
  selectionChange: [selection: any[]]
  export: [selection: any[]]
  refresh: []
  retry: []
}>()

// Reactive data
const searchQuery = ref('')
const selectedFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(props.pageSize)
const selectedRows = ref<any[]>([])
const sortState = ref(props.defaultSort)
const isExporting = ref(false)

// Computed properties
const filteredData = computed(() => {
  let result = props.data

  // Apply search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(row => {
      return props.columns.some(column => {
        const value = row[column.prop]
        return value && value.toString().toLowerCase().includes(query)
      })
    })
  }

  // Apply column filter
  if (selectedFilter.value) {
    // Implement custom filter logic based on filter type
    result = result.filter(row => {
      // Example: filter by status
      return row.status === selectedFilter.value
    })
  }

  return result
})

const totalItems = computed(() => filteredData.value.length)

const startIndex = computed(() => {
  return (currentPage.value - 1) * pageSize.value + 1
})

const endIndex = computed(() => {
  return Math.min(currentPage.value * pageSize.value, totalItems.value)
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredData.value.slice(start, end)
})

const visibleColumns = computed(() => {
  return props.columns.filter(column => column.visible !== false)
})

const hasActions = computed(() => {
  return props.actions.length > 0
})

const exportButtonLabel = computed(() => {
  return `Export ${selectedRows.value.length || 'all'} items`
})

// Methods
const handleSearch = (query: string) => {
  currentPage.value = 1
  emit('search', query)
}

const handleFilter = (filter: string) => {
  currentPage.value = 1
  emit('filter', filter)
}

const handleSortChange = (sort: { prop: string; order: 'ascending' | 'descending' }) => {
  sortState.value = sort
  emit('sort', sort)
}

const handleSelectionChange = (selection: any[]) => {
  selectedRows.value = selection
  emit('selectionChange', selection)
}

const handlePageChange = (page: number) => {
  currentPage.value = page
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleExport = async () => {
  isExporting.value = true
  
  try {
    await withErrorHandling(
      async () => {
        emit('export', selectedRows.value.length > 0 ? selectedRows.value : props.data)
        ElMessage.success('Export completed successfully')
      },
      'Data Export',
      { showLoading: false }
    )
  } finally {
    isExporting.value = false
  }
}

const handleRefresh = () => {
  emit('refresh')
}

const handleRetry = () => {
  emit('retry')
}

const isRowSelectable = (row: any) => {
  // Implement custom selection logic
  return true
}

const getRowActions = (row: any) => {
  return props.actions.filter(action => 
    !action.condition || action.condition(row)
  )
}

const getStatusType = (status: string) => {
  const statusMap: Record<string, string> = {
    'active': 'success',
    'inactive': 'info',
    'pending': 'warning',
    'error': 'danger'
  }
  return statusMap[status.toLowerCase()] || 'info'
}

const formatDate = (value: any) => {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return value
  }
}

const formatNumber = (value: any) => {
  if (value === null || value === undefined) return ''
  return Number(value).toLocaleString(props.numberFormat)
}

// Accessibility
const announceChanges = () => {
  const message = `Showing ${startIndex.value} to ${endIndex.value} of ${totalItems.value} items`
  AccessibilityHelper.announce(message, 'polite')
}

// Watch for changes and announce them
watch([currentPage, pageSize, totalItems], announceChanges)

// Lifecycle
onMounted(() => {
  // Announce initial table state
  announceChanges()
  
  // Set up keyboard navigation for the table
  nextTick(() => {
    const tableElement = document.querySelector('.data-table')
    if (tableElement) {
      AccessibilityHelper.setupKeyboardNavigation(tableElement as HTMLElement, {
        orientation: 'vertical',
        loop: true
      })
    }
  })
})
</script>

<style scoped>
.data-table-container {
  background: var(--color-bg-white);
  border-radius: var(--border-radius-large);
  border: 1px solid var(--color-border-light);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  transition: var(--transition-base);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-lg);
  gap: var(--spacing-lg);
}

.table-header-left {
  flex: 1;
}

.table-title {
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
}

.table-description {
  color: var(--color-text-secondary);
  font-size: var(--font-size-small);
  margin: 0;
}

.table-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.search-container,
.filter-container {
  min-width: 200px;
}

.search-input,
.filter-select {
  width: 100%;
}

.export-button {
  white-space: nowrap;
}

.table-loading {
  position: relative;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-overlay);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  z-index: var(--z-index-top);
}

.table-error {
  text-align: center;
  padding: var(--spacing-xl);
}

.retry-button {
  margin-top: var(--spacing-md);
}

.table-empty {
  text-align: center;
  padding: var(--spacing-xl);
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
}

.empty-icon {
  font-size: 48px;
  color: var(--color-text-placeholder);
}

.empty-title {
  font-size: var(--font-size-medium);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.empty-description {
  color: var(--color-text-secondary);
  margin: 0;
}

.table-wrapper {
  overflow-x: auto;
}

.table-info {
  font-size: var(--font-size-small);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
  padding: var(--spacing-xs) 0;
}

.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.table-cell-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.table-actions {
  display: flex;
  gap: var(--spacing-xs);
}

.action-button {
  min-width: auto;
  padding: var(--spacing-xs) var(--spacing-sm);
}

.table-pagination {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-light);
}

.selection-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary-bg);
  border-radius: var(--border-radius-base);
  border: 1px solid var(--color-primary-light);
}

.selection-count {
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}

.selection-actions {
  display: flex;
  gap: var(--spacing-xs);
}

/* Responsive design */
@media (max-width: 768px) {
  .table-header {
    flex-direction: column;
    align-items: stretch;
  }

  .table-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .search-container,
  .filter-container {
    min-width: auto;
  }

  .export-button {
    width: 100%;
  }

  .selection-info {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-sm);
  }

  .selection-actions {
    justify-content: center;
  }
}

@media (max-width: 375px) {
  .data-table-container {
    padding: var(--spacing-md);
  }

  .table-controls {
    gap: var(--spacing-xs);
  }

  .table-actions {
    flex-direction: column;
  }

  .action-button {
    width: 100%;
  }
}

/* Focus styles for accessibility */
.table-actions:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
  border-radius: var(--border-radius-small);
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .data-table-container {
    border-width: 2px;
  }
  
  .selection-info {
    border-width: 2px;
  }
}
</style>
