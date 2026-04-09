<template>
  <div class="report-editor">
    <!-- 顶部工具栏 -->
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <el-button :icon="Back" @click="handleBack">返回</el-button>
        <el-divider direction="vertical" />
        <el-input
          v-model="reportName"
          placeholder="报告名称"
          style="width: 300px"
        />
      </div>
      
      <div class="toolbar-center">
        <el-button-group>
          <el-button :icon="ZoomOut" @click="handleZoom(-10)">缩小</el-button>
          <el-button>{{ zoomLevel }}%</el-button>
          <el-button :icon="ZoomIn" @click="handleZoom(10)">放大</el-button>
        </el-button-group>
        
        <el-divider direction="vertical" />
        
        <el-button-group>
          <el-button :icon="RefreshLeft" :disabled="!canUndo" @click="handleUndo">撤销</el-button>
          <el-button :icon="RefreshRight" :disabled="!canRedo" @click="handleRedo">重做</el-button>
        </el-button-group>
      </div>
      
      <div class="toolbar-right">
        <el-button :icon="View" @click="handlePreview">预览</el-button>
        <el-button :icon="Download" @click="handleExport">导出</el-button>
        <el-button type="primary" :icon="Check" @click="handleSave">保存</el-button>
      </div>
    </div>
    
    <!-- 主编辑区域 -->
    <div class="editor-content">
      <!-- 左侧组件面板 -->
      <div class="component-panel" :class="{ collapsed: leftPanelCollapsed }">
        <div class="panel-header">
          <span>组件库</span>
          <el-button
            text
            :icon="leftPanelCollapsed ? DArrowRight : DArrowLeft"
            @click="leftPanelCollapsed = !leftPanelCollapsed"
          />
        </div>
        
        <div v-if="!leftPanelCollapsed" class="panel-content">
          <el-collapse v-model="activeComponentCategories" accordion>
            <!-- 章节组件 -->
            <el-collapse-item name="section" title="章节">
              <div class="component-list">
                <div
                  v-for="comp in sectionComponents"
                  :key="comp.type"
                  class="component-item"
                  draggable="true"
                  @dragstart="handleDragStart($event, comp)"
                >
                  <el-icon><component :is="comp.icon" /></el-icon>
                  <span>{{ comp.name }}</span>
                </div>
              </div>
            </el-collapse-item>
            
            <!-- 图表组件 -->
            <el-collapse-item name="chart" title="图表">
              <div class="component-list">
                <div
                  v-for="comp in chartComponents"
                  :key="comp.type"
                  class="component-item"
                  draggable="true"
                  @dragstart="handleDragStart($event, comp)"
                >
                  <el-icon><component :is="comp.icon" /></el-icon>
                  <span>{{ comp.name }}</span>
                </div>
              </div>
            </el-collapse-item>
            
            <!-- 内容组件 -->
            <el-collapse-item name="content" title="内容">
              <div class="component-list">
                <div
                  v-for="comp in contentComponents"
                  :key="comp.type"
                  class="component-item"
                  draggable="true"
                  @dragstart="handleDragStart($event, comp)"
                >
                  <el-icon><component :is="comp.icon" /></el-icon>
                  <span>{{ comp.name }}</span>
                </div>
              </div>
            </el-collapse-item>
            
            <!-- 布局组件 -->
            <el-collapse-item name="layout" title="布局">
              <div class="component-list">
                <div
                  v-for="comp in layoutComponents"
                  :key="comp.type"
                  class="component-item"
                  draggable="true"
                  @dragstart="handleDragStart($event, comp)"
                >
                  <el-icon><component :is="comp.icon" /></el-icon>
                  <span>{{ comp.name }}</span>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
      
      <!-- 中间画布区域 -->
      <div class="canvas-area">
        <div class="canvas-wrapper" :style="{ transform: `scale(${zoomLevel / 100})` }">
          <div
            v-for="(page, index) in pages"
            :key="page.id"
            class="page-canvas"
            :class="{ active: currentPageIndex === index }"
            :style="getPageStyle()"
            @click="handlePageClick(index)"
            @drop="handleDrop($event, page.id)"
            @dragover.prevent
          >
            <!-- 页面组件 -->
            <div
              v-for="component in page.components"
              :key="component.id"
              class="report-component"
              :class="{ selected: selectedComponent?.id === component.id }"
              :style="getComponentStyle(component)"
              @click.stop="handleSelectComponent(component)"
              @mousedown="handleComponentMouseDown($event, component)"
            >
              <component
                :is="getComponentRenderer(component.type)"
                v-bind="component.config"
              />
              
              <!-- 调整手柄 -->
              <div v-if="selectedComponent?.id === component.id" class="resize-handles">
                <div class="resize-handle nw" @mousedown.stop="handleResizeStart($event, 'nw')"></div>
                <div class="resize-handle ne" @mousedown.stop="handleResizeStart($event, 'ne')"></div>
                <div class="resize-handle sw" @mousedown.stop="handleResizeStart($event, 'sw')"></div>
                <div class="resize-handle se" @mousedown.stop="handleResizeStart($event, 'se')"></div>
              </div>
            </div>
            
            <!-- 页码 -->
            <div class="page-number">{{ index + 1 }}</div>
          </div>
        </div>
      </div>
      
      <!-- 右侧属性面板 -->
      <div class="property-panel" :class="{ collapsed: rightPanelCollapsed }">
        <div class="panel-header">
          <span>属性</span>
          <el-button
            text
            :icon="rightPanelCollapsed ? DArrowLeft : DArrowRight"
            @click="rightPanelCollapsed = !rightPanelCollapsed"
          />
        </div>
        
        <div v-if="!rightPanelCollapsed" class="panel-content">
          <el-tabs v-model="activePropertyTab">
            <!-- 组件属性 -->
            <el-tab-pane label="组件" name="component">
              <div v-if="selectedComponent" class="property-form">
                <el-form label-position="top" size="small">
                  <!-- 通用属性 -->
                  <el-form-item label="组件名称">
                    <el-input v-model="selectedComponent.name" />
                  </el-form-item>
                  
                  <!-- 位置和大小 -->
                  <el-form-item label="位置">
                    <el-row :gutter="8">
                      <el-col :span="12">
                        <el-input-number
                          v-model="selectedComponent.position.x"
                          :min="0"
                          controls-position="right"
                          style="width: 100%"
                        >
                          <template #prefix>X:</template>
                        </el-input-number>
                      </el-col>
                      <el-col :span="12">
                        <el-input-number
                          v-model="selectedComponent.position.y"
                          :min="0"
                          controls-position="right"
                          style="width: 100%"
                        >
                          <template #prefix>Y:</template>
                        </el-input-number>
                      </el-col>
                    </el-row>
                  </el-form-item>
                  
                  <el-form-item label="大小">
                    <el-row :gutter="8">
                      <el-col :span="12">
                        <el-input-number
                          v-model="selectedComponent.size.width"
                          :min="50"
                          controls-position="right"
                          style="width: 100%"
                        >
                          <template #prefix>W:</template>
                        </el-input-number>
                      </el-col>
                      <el-col :span="12">
                        <el-input-number
                          v-model="selectedComponent.size.height"
                          :min="30"
                          controls-position="right"
                          style="width: 100%"
                        >
                          <template #prefix>H:</template>
                        </el-input-number>
                      </el-col>
                    </el-row>
                  </el-form-item>
                  
                  <!-- 组件特定配置 -->
                  <component
                    :is="getPropertyEditor(selectedComponent.type)"
                    v-model="selectedComponent.config"
                  />
                </el-form>
              </div>
              <el-empty v-else description="请选择一个组件" />
            </el-tab-pane>
            
            <!-- 页面设置 -->
            <el-tab-pane label="页面" name="page">
              <div class="property-form">
                <el-form label-position="top" size="small">
                  <el-form-item label="页面尺寸">
                    <el-select v-model="pageSettings.size">
                      <el-option label="A4" value="A4" />
                      <el-option label="A3" value="A3" />
                      <el-option label="Letter" value="Letter" />
                    </el-select>
                  </el-form-item>
                  
                  <el-form-item label="页面方向">
                    <el-radio-group v-model="pageSettings.orientation">
                      <el-radio label="portrait">纵向</el-radio>
                      <el-radio label="landscape">横向</el-radio>
                    </el-radio-group>
                  </el-form-item>
                  
                  <el-form-item label="页边距">
                    <el-row :gutter="8">
                      <el-col :span="12">
                        <el-input-number
                          v-model="pageSettings.margins.top"
                          :min="0"
                          controls-position="right"
                          style="width: 100%"
                        >
                          <template #prefix>上:</template>
                        </el-input-number>
                      </el-col>
                      <el-col :span="12">
                        <el-input-number
                          v-model="pageSettings.margins.bottom"
                          :min="0"
                          controls-position="right"
                          style="width: 100%"
                        >
                          <template #prefix>下:</template>
                        </el-input-number>
                      </el-col>
                    </el-row>
                    <el-row :gutter="8" style="margin-top: 8px">
                      <el-col :span="12">
                        <el-input-number
                          v-model="pageSettings.margins.left"
                          :min="0"
                          controls-position="right"
                          style="width: 100%"
                        >
                          <template #prefix>左:</template>
                        </el-input-number>
                      </el-col>
                      <el-col :span="12">
                        <el-input-number
                          v-model="pageSettings.margins.right"
                          :min="0"
                          controls-position="right"
                          style="width: 100%"
                        >
                          <template #prefix>右:</template>
                        </el-input-number>
                      </el-col>
                    </el-row>
                  </el-form-item>
                </el-form>
              </div>
            </el-tab-pane>
            
            <!-- 变量管理 -->
            <el-tab-pane label="变量" name="variables">
              <div class="variables-panel">
                <el-button
                  type="primary"
                  size="small"
                  :icon="Plus"
                  style="width: 100%; margin-bottom: 12px"
                  @click="handleAddVariable"
                >
                  添加变量
                </el-button>
                
                <el-collapse v-model="activeVariableCategories">
                  <el-collapse-item name="system" title="系统变量">
                    <div class="variable-list">
                      <div
                        v-for="variable in systemVariables"
                        :key="variable.name"
                        class="variable-item"
                        @click="handleInsertVariable(variable)"
                      >
                        <el-tag size="small">{{ variable.name }}</el-tag>
                        <span class="variable-desc">{{ variable.description }}</span>
                      </div>
                    </div>
                  </el-collapse-item>
                  
                  <el-collapse-item name="data" title="数据变量">
                    <div class="variable-list">
                      <div
                        v-for="variable in dataVariables"
                        :key="variable.name"
                        class="variable-item"
                        @click="handleInsertVariable(variable)"
                      >
                        <el-tag size="small" type="success">{{ variable.name }}</el-tag>
                        <span class="variable-desc">{{ variable.description }}</span>
                      </div>
                    </div>
                  </el-collapse-item>
                  
                  <el-collapse-item name="custom" title="自定义变量">
                    <div class="variable-list">
                      <div
                        v-for="variable in customVariables"
                        :key="variable.name"
                        class="variable-item"
                        @click="handleInsertVariable(variable)"
                      >
                        <el-tag size="small" type="warning">{{ variable.name }}</el-tag>
                        <span class="variable-desc">{{ variable.description }}</span>
                        <el-button
                          text
                          :icon="Delete"
                          size="small"
                          @click.stop="handleDeleteVariable(variable)"
                        />
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>
    
    <!-- 底部页面导航 -->
    <div class="page-navigation">
      <div class="page-thumbnails">
        <div
          v-for="(page, index) in pages"
          :key="page.id"
          class="page-thumbnail"
          :class="{ active: currentPageIndex === index }"
          @click="handlePageClick(index)"
        >
          <div class="thumbnail-preview">
            <span>{{ index + 1 }}</span>
          </div>
          <el-dropdown trigger="click" @command="(cmd) => handlePageAction(cmd, index)">
            <el-button text size="small" :icon="MoreFilled" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="duplicate" :icon="CopyDocument">复制</el-dropdown-item>
                <el-dropdown-item command="delete" :icon="Delete">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        
        <div class="page-thumbnail add-page" @click="handleAddPage">
          <el-icon :size="24"><Plus /></el-icon>
        </div>
      </div>
    </div>
    
    <!-- 变量编辑对话框 -->
    <el-dialog v-model="showVariableDialog" title="添加自定义变量" width="500px">
      <el-form :model="newVariable" label-width="80px">
        <el-form-item label="变量名">
          <el-input v-model="newVariable.name" placeholder="例如: userName" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newVariable.description" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newVariable.type">
            <el-option label="文本" value="string" />
            <el-option label="数字" value="number" />
            <el-option label="日期" value="date" />
            <el-option label="布尔" value="boolean" />
          </el-select>
        </el-form-item>
        <el-form-item label="默认值">
          <el-input v-model="newVariable.defaultValue" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showVariableDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveVariable">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, markRaw } from 'vue';
import { ElMessage } from 'element-plus';
import {
  Back, ZoomIn, ZoomOut, RefreshLeft, RefreshRight, View, Download, Check,
  DArrowLeft, DArrowRight, Plus, Delete, MoreFilled, CopyDocument,
  Document, Histogram, Picture, Grid, Minus,
} from '@element-plus/icons-vue';

// 组件定义
const sectionComponents = [
  { type: 'cover', name: '封面', icon: markRaw(Document) },
  { type: 'toc', name: '目录', icon: markRaw(Document) },
  { type: 'summary', name: '摘要', icon: markRaw(Document) },
  { type: 'header', name: '页眉', icon: markRaw(Document) },
  { type: 'footer', name: '页脚', icon: markRaw(Document) },
];

const chartComponents = [
  { type: 'chart', name: '图表', icon: markRaw(Histogram) },
  { type: 'table', name: '表格', icon: markRaw(Grid) },
];

const contentComponents = [
  { type: 'text', name: '文本', icon: markRaw(Document) },
  { type: 'image', name: '图片', icon: markRaw(Picture) },
];

const layoutComponents = [
  { type: 'divider', name: '分隔线', icon: markRaw(Minus) },
  { type: 'pagebreak', name: '分页符', icon: markRaw(Document) },
];

// State
const reportName = ref('未命名报告');
const zoomLevel = ref(100);
const leftPanelCollapsed = ref(false);
const rightPanelCollapsed = ref(false);
const activeComponentCategories = ref(['section']);
const activePropertyTab = ref('component');
const activeVariableCategories = ref(['system']);
const currentPageIndex = ref(0);
const selectedComponent = ref<any>(null);
const showVariableDialog = ref(false);

const pageSettings = ref({
  size: 'A4',
  orientation: 'portrait',
  margins: { top: 20, right: 20, bottom: 20, left: 20 },
});

const pages = ref([
  {
    id: 'page-1',
    name: '第1页',
    components: [],
  },
]);

// 系统变量
const systemVariables = ref([
  { name: 'currentDate', description: '当前日期', value: new Date().toLocaleDateString() },
  { name: 'currentTime', description: '当前时间', value: new Date().toLocaleTimeString() },
  { name: 'reportPeriod', description: '报告周期', value: '2024-01-01 至 2024-12-31' },
  { name: 'generatedBy', description: '生成者', value: '系统管理员' },
  { name: 'pageNumber', description: '页码', value: '{{pageNumber}}' },
  { name: 'totalPages', description: '总页数', value: '{{totalPages}}' },
]);

// 数据变量
const dataVariables = ref([
  { name: 'totalCount', description: '总数据量', value: '10000' },
  { name: 'positiveRate', description: '正面情感占比', value: '65%' },
  { name: 'negativeRate', description: '负面情感占比', value: '20%' },
  { name: 'neutralRate', description: '中性情感占比', value: '15%' },
]);

// 自定义变量
const customVariables = ref<any[]>([]);

const newVariable = ref({
  name: '',
  description: '',
  type: 'string',
  defaultValue: '',
});

const canUndo = computed(() => false);
const canRedo = computed(() => false);

// 页面样式
function getPageStyle() {
  const sizes: Record<string, { width: number; height: number }> = {
    A4: { width: 794, height: 1123 },
    A3: { width: 1123, height: 1587 },
    Letter: { width: 816, height: 1056 },
  };
  
  const size = sizes[pageSettings.value.size];
  const { width, height } = pageSettings.value.orientation === 'portrait'
    ? size
    : { width: size.height, height: size.width };
  
  return {
    width: `${width}px`,
    height: `${height}px`,
    padding: `${pageSettings.value.margins.top}px ${pageSettings.value.margins.right}px ${pageSettings.value.margins.bottom}px ${pageSettings.value.margins.left}px`,
  };
}

// 组件样式
function getComponentStyle(component: any) {
  return {
    left: `${component.position.x}px`,
    top: `${component.position.y}px`,
    width: `${component.size.width}px`,
    height: `${component.size.height}px`,
  };
}

// 拖拽开始
function handleDragStart(event: DragEvent, component: any) {
  event.dataTransfer!.effectAllowed = 'copy';
  event.dataTransfer!.setData('component', JSON.stringify(component));
}

// 放置组件
function handleDrop(event: DragEvent, pageId: string) {
  const data = event.dataTransfer!.getData('component');
  if (!data) return;
  
  const component = JSON.parse(data);
  const rect = (event.target as HTMLElement).getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  
  const newComponent = {
    id: `comp-${Date.now()}`,
    type: component.type,
    name: component.name,
    position: { x, y },
    size: { width: 300, height: 200 },
    config: {},
  };
  
  const page = pages.value.find(p => p.id === pageId);
  if (page) {
    page.components.push(newComponent);
  }
}

// 选择组件
function handleSelectComponent(component: any) {
  selectedComponent.value = component;
}

// 组件移动
function handleComponentMouseDown(event: MouseEvent, component: any) {
  // 实现拖拽移动逻辑
}

// 调整大小
function handleResizeStart(event: MouseEvent, direction: string) {
  // 实现调整大小逻辑
}

// 页面操作
function handlePageClick(index: number) {
  currentPageIndex.value = index;
}

function handleAddPage() {
  pages.value.push({
    id: `page-${Date.now()}`,
    name: `第${pages.value.length + 1}页`,
    components: [],
  });
}

function handlePageAction(command: string, index: number) {
  if (command === 'duplicate') {
    const page = pages.value[index];
    pages.value.splice(index + 1, 0, {
      ...page,
      id: `page-${Date.now()}`,
      name: `${page.name} - 副本`,
    });
  } else if (command === 'delete') {
    if (pages.value.length > 1) {
      pages.value.splice(index, 1);
    } else {
      ElMessage.warning('至少保留一页');
    }
  }
}

// 变量操作
function handleAddVariable() {
  showVariableDialog.value = true;
  newVariable.value = {
    name: '',
    description: '',
    type: 'string',
    defaultValue: '',
  };
}

function handleSaveVariable() {
  if (!newVariable.value.name) {
    ElMessage.warning('请输入变量名');
    return;
  }
  
  customVariables.value.push({ ...newVariable.value });
  showVariableDialog.value = false;
  ElMessage.success('变量已添加');
}

function handleDeleteVariable(variable: any) {
  const index = customVariables.value.indexOf(variable);
  if (index !== -1) {
    customVariables.value.splice(index, 1);
  }
}

function handleInsertVariable(variable: any) {
  // 插入变量到选中的文本组件
  ElMessage.info(`插入变量: {{${variable.name}}}`);
}

// 工具栏操作
function handleBack() {
  // 返回
}

function handleZoom(delta: number) {
  zoomLevel.value = Math.max(50, Math.min(200, zoomLevel.value + delta));
}

function handleUndo() {
  // 撤销
}

function handleRedo() {
  // 重做
}

function handlePreview() {
  // 预览
}

function handleExport() {
  // 导出
}

function handleSave() {
  // 保存
  ElMessage.success('保存成功');
}

// 组件渲染器
function getComponentRenderer(type: string) {
  // 返回对应的组件
  return 'div';
}

// 属性编辑器
function getPropertyEditor(type: string) {
  // 返回对应的属性编辑器
  return 'div';
}
</script>

<style scoped lang="scss">
.report-editor {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  
  .toolbar-left,
  .toolbar-center,
  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.editor-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.component-panel,
.property-panel {
  width: 280px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  
  &.collapsed {
    width: 40px;
  }
  
  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    font-weight: 500;
    border-bottom: 1px solid #e4e7ed;
  }
  
  .panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
  }
}

.property-panel {
  border-right: none;
  border-left: 1px solid #e4e7ed;
}

.component-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.component-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  background: #f5f7fa;
  border-radius: 4px;
  cursor: grab;
  transition: all 0.2s;
  
  &:hover {
    background: #ecf5ff;
    transform: translateY(-2px);
  }
  
  &:active {
    cursor: grabbing;
  }
  
  span {
    font-size: 12px;
    color: #606266;
  }
}

.canvas-area {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background: #e8e8e8;
}

.canvas-wrapper {
  transform-origin: top center;
  transition: transform 0.2s;
}

.page-canvas {
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  margin: 0 auto 20px;
  position: relative;
  
  &.active {
    box-shadow: 0 0 0 2px #409EFF;
  }
}

.report-component {
  position: absolute;
  border: 1px dashed transparent;
  cursor: move;
  
  &.selected {
    border-color: #409EFF;
    background: rgba(64, 158, 255, 0.05);
  }
  
  &:hover {
    border-color: #409EFF;
  }
}

.resize-handles {
  .resize-handle {
    position: absolute;
    width: 8px;
    height: 8px;
    background: #409EFF;
    border: 1px solid #fff;
    border-radius: 50%;
    
    &.nw { top: -4px; left: -4px; cursor: nw-resize; }
    &.ne { top: -4px; right: -4px; cursor: ne-resize; }
    &.sw { bottom: -4px; left: -4px; cursor: sw-resize; }
    &.se { bottom: -4px; right: -4px; cursor: se-resize; }
  }
}

.page-number {
  position: absolute;
  bottom: 10px;
  right: 10px;
  font-size: 12px;
  color: #909399;
}

.page-navigation {
  height: 120px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  padding: 12px;
  overflow-x: auto;
}

.page-thumbnails {
  display: flex;
  gap: 12px;
  height: 100%;
}

.page-thumbnail {
  width: 80px;
  height: 100%;
  border: 2px solid #e4e7ed;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  
  &:hover {
    border-color: #409EFF;
  }
  
  &.active {
    border-color: #409EFF;
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
  }
  
  &.add-page {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f5f7fa;
    
    &:hover {
      background: #ecf5ff;
    }
  }
}

.thumbnail-preview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
  font-size: 24px;
  color: #909399;
}

.variable-list {
  .variable-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s;
    
    &:hover {
      background: #f5f7fa;
    }
    
    .variable-desc {
      flex: 1;
      font-size: 12px;
      color: #909399;
    }
  }
}

.property-form {
  padding: 12px;
}
</style>
