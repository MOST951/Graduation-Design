<template>
  <div class="visualization-module">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-section">
        <span class="section-label">图表类型:</span>
        <el-select v-model="selectedChartType" placeholder="选择图表" style="width: 150px" size="small">
          <el-option label="柱状图" value="bar" />
          <el-option label="折线图" value="line" />
          <el-option label="饼图" value="pie" />
          <el-option label="散点图" value="scatter" />
          <el-option label="热力图" value="heatmap" />
          <el-option label="雷达图" value="radar" />
        </el-select>
      </div>
      
      <el-divider direction="vertical" />
      
      <div class="toolbar-section">
        <span class="section-label">数据源:</span>
        <el-select v-model="selectedDataSource" placeholder="选择数据源" style="width: 150px" size="small">
          <el-option label="情感分析结果" value="sentiment" />
          <el-option label="用户行为数据" value="behavior" />
          <el-option label="热点话题" value="topics" />
          <el-option label="实时监控" value="monitor" />
        </el-select>
      </div>
      
      <el-divider direction="vertical" />
      
      <div class="toolbar-section">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          size="small"
          style="width: 240px"
        />
      </div>
      
      <el-divider direction="vertical" />
      
      <el-button-group size="small">
        <el-button :icon="Plus" type="primary" @click="addChart">添加图表</el-button>
        <el-button :icon="Download" @click="exportDashboard">导出</el-button>
        <el-button :icon="Share" @click="shareDashboard">分享</el-button>
      </el-button-group>
      
      <div class="toolbar-right">
        <el-button
          :icon="showPropertyPanel ? 'ArrowRight' : 'ArrowLeft'"
          circle
          size="small"
          @click="showPropertyPanel = !showPropertyPanel"
        />
      </div>
    </div>
    
    <!-- 主工作区 -->
    <div class="workbench-layout">
      <!-- 可拖拽画布 -->
      <main class="canvas-area" :class="{ 'panel-collapsed': !showPropertyPanel }">
        <grid-layout
          v-model:layout="layout"
          :col-num="12"
          :row-height="30"
          :is-draggable="true"
          :is-resizable="true"
          :vertical-compact="true"
          :margin="[10, 10]"
          :use-css-transforms="true"
          @change="handleZoomChange"
        >
        </grid-layout>
        <el-button size="small" @click="store.resetCanvasView()">重置</el-button>
        <el-button size="small" @click="handleFitToCanvas">适应</el-button>
      </main>
    </div>
    
    <div class="workbench-content">
      <!-- 左侧组件库面板 -->
      <div class="component-panel" :class="{ collapsed: !store.componentPanelExpanded }">
        <div class="panel-header">
          <span>组件库</span>
          <el-button
            :icon="store.componentPanelExpanded ? DArrowLeft : DArrowRight"
            text
            @click="store.componentPanelExpanded = !store.componentPanelExpanded"
          />
        </div>
        
        <template v-if="store.componentPanelExpanded">
          <div class="panel-search">
            <el-input
              v-model="store.searchKeyword"
              placeholder="搜索组件..."
              :prefix-icon="Search"
              clearable
            />
          </div>
          
          <div class="category-tabs">
            <el-radio-group v-model="store.selectedCategory" size="small">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="chart">图表</el-radio-button>
              <el-radio-button label="text">文本</el-radio-button>
              <el-radio-button label="control">控件</el-radio-button>
              <el-radio-button label="layout">布局</el-radio-button>
            </el-radio-group>
          </div>
          
          <div class="component-list">
            <div
              v-for="comp in store.filteredComponents"
              :key="comp.type"
              class="component-item"
              draggable="true"
              @dragstart="handleDragStart($event, comp)"
              @click="handleAddComponent(comp.type)"
            >
              <el-icon :size="24">
                <component :is="comp.icon" />
              </el-icon>
              <span class="component-name">{{ comp.name }}</span>
            </div>
          </div>
        </template>
      </div>
      
      <!-- 中间画布区域 -->
      <div
        ref="canvasContainerRef"
        class="canvas-container"
        @drop="handleDrop"
        @dragover.prevent
        @click="handleCanvasClick"
      >
        <div
          ref="canvasRef"
          class="canvas"
          :style="canvasStyle"
        >
          <!-- 网格背景 -->
          <div v-if="store.currentLayout.showGrid" class="canvas-grid" :style="gridStyle"></div>
          
          <!-- 组件渲染 -->
          <div
            v-for="comp in store.canvasComponents"
            :key="comp.id"
            class="canvas-component"
            :class="{
              selected: store.selectedComponentIds.includes(comp.id),
              locked: comp.locked,
              hidden: !comp.visible,
            }"
            :style="getComponentStyle(comp)"
            @mousedown.stop="handleComponentMouseDown($event, comp)"
            @click.stop="handleComponentClick($event, comp)"
          >
            <!-- 组件内容 -->
            <component
              :is="getComponentRenderer(comp.type)"
              v-bind="comp.props"
              :style="getComponentInnerStyle(comp)"
            />
            
            <!-- 选中状态边框和控制点 -->
            <template v-if="store.selectedComponentIds.includes(comp.id) && !comp.locked">
              <div class="resize-handle nw" @mousedown.stop="handleResizeStart($event, comp, 'nw')"></div>
              <div class="resize-handle ne" @mousedown.stop="handleResizeStart($event, comp, 'ne')"></div>
              <div class="resize-handle sw" @mousedown.stop="handleResizeStart($event, comp, 'sw')"></div>
              <div class="resize-handle se" @mousedown.stop="handleResizeStart($event, comp, 'se')"></div>
              <div class="resize-handle n" @mousedown.stop="handleResizeStart($event, comp, 'n')"></div>
              <div class="resize-handle s" @mousedown.stop="handleResizeStart($event, comp, 's')"></div>
              <div class="resize-handle w" @mousedown.stop="handleResizeStart($event, comp, 'w')"></div>
              <div class="resize-handle e" @mousedown.stop="handleResizeStart($event, comp, 'e')"></div>
            </template>
            
            <!-- 锁定图标 -->
            <div v-if="comp.locked" class="lock-indicator">
              <el-icon><Lock /></el-icon>
            </div>
          </div>
          
          <!-- 选择框 -->
          <div v-if="selectionBox" class="selection-box" :style="selectionBoxStyle"></div>
        </div>
      </div>
      
      <!-- 右侧属性面板 -->
      <div class="property-panel" :class="{ collapsed: !store.propertyPanelExpanded }">
        <div class="panel-header">
          <span>属性配置</span>
          <el-button
            :icon="store.propertyPanelExpanded ? DArrowRight : DArrowLeft"
            text
            @click="store.propertyPanelExpanded = !store.propertyPanelExpanded"
          />
        </div>
        
        <template v-if="store.propertyPanelExpanded">
          <template v-if="store.activeComponent">
            <el-tabs v-model="activePropertyTab">
              <el-tab-pane label="属性" name="props">
                <div class="property-section">
                  <div class="property-title">基础属性</div>
                  <el-form label-position="top" size="small">
                    <el-form-item label="位置 X">
                      <el-input-number
                        :model-value="store.activeComponent.x"
                        :min="0"
                        @change="(val) => updateComponentProp('x', val)"
                      />
                    </el-form-item>
                    <el-form-item label="位置 Y">
                      <el-input-number
                        :model-value="store.activeComponent.y"
                        :min="0"
                        @change="(val) => updateComponentProp('y', val)"
                      />
                    </el-form-item>
                    <el-form-item label="宽度">
                      <el-input-number
                        :model-value="store.activeComponent.width"
                        :min="50"
                        @change="(val) => updateComponentProp('width', val)"
                      />
                    </el-form-item>
                    <el-form-item label="高度">
                      <el-input-number
                        :model-value="store.activeComponent.height"
                        :min="50"
                        @change="(val) => updateComponentProp('height', val)"
                      />
                    </el-form-item>
                  </el-form>
                </div>
                
                <div class="property-section">
                  <div class="property-title">组件属性</div>
                  <el-form label-position="top" size="small">
                    <template v-for="(value, key) in store.activeComponent.props" :key="key">
                      <el-form-item :label="String(key)">
                        <template v-if="typeof value === 'boolean'">
                          <el-switch
                            :model-value="value"
                            @change="(val) => updateComponentProps(String(key), val)"
                          />
                        </template>
                        <template v-else-if="typeof value === 'number'">
                          <el-input-number
                            :model-value="value"
                            @change="(val) => updateComponentProps(String(key), val)"
                          />
                        </template>
                        <template v-else-if="typeof value === 'string'">
                          <el-input
                            :model-value="value"
                            @change="(val) => updateComponentProps(String(key), val)"
                          />
                        </template>
                        <template v-else>
                          <el-input
                            :model-value="JSON.stringify(value)"
                            type="textarea"
                            :rows="2"
                            @change="(val) => updateComponentPropsJson(String(key), val)"
                          />
                        </template>
                      </el-form-item>
                    </template>
                  </el-form>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="样式" name="styles">
                <div class="property-section">
                  <div class="property-title">背景与边框</div>
                  <el-form label-position="top" size="small">
                    <el-form-item label="背景色">
                      <el-color-picker
                        :model-value="store.activeComponent.styles.backgroundColor"
                        show-alpha
                        @change="(val) => updateComponentStyle('backgroundColor', val)"
                      />
                    </el-form-item>
                    <el-form-item label="边框颜色">
                      <el-color-picker
                        :model-value="store.activeComponent.styles.borderColor"
                        @change="(val) => updateComponentStyle('borderColor', val)"
                      />
                    </el-form-item>
                    <el-form-item label="边框宽度">
                      <el-slider
                        :model-value="store.activeComponent.styles.borderWidth"
                        :min="0"
                        :max="10"
                        @change="(val) => updateComponentStyle('borderWidth', val)"
                      />
                    </el-form-item>
                    <el-form-item label="圆角">
                      <el-slider
                        :model-value="store.activeComponent.styles.borderRadius"
                        :min="0"
                        :max="50"
                        @change="(val) => updateComponentStyle('borderRadius', val)"
                      />
                    </el-form-item>
                    <el-form-item label="透明度">
                      <el-slider
                        :model-value="store.activeComponent.styles.opacity"
                        :min="0"
                        :max="1"
                        :step="0.1"
                        @change="(val) => updateComponentStyle('opacity', val)"
                      />
                    </el-form-item>
                  </el-form>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="联动" name="bindage">
                <div class="property-section">
                  <div class="property-title">图表联动</div>
                  <div class="linkage-summary">
                    <p v-if="getComponentLinkageInfo(store.activeComponent.id).asSource > 0">
                      <el-tag size="small" type="primary">源</el-tag>
                      作为源触发 {{ getComponentLinkageInfo(store.activeComponent.id).asSource }} 条规则
                    </p>
                    <p v-if="getComponentLinkageInfo(store.activeComponent.id).asTarget > 0">
                      <el-tag size="small" type="success">目标</el-tag>
                      作为目标接收 {{ getComponentLinkageInfo(store.activeComponent.id).asTarget }} 条规则
                    </p>
                    <p v-if="getComponentLinkageInfo(store.activeComponent.id).asSource === 0 && getComponentLinkageInfo(store.activeComponent.id).asTarget === 0" class="no-linkage">
                      暂无联动配置
                    </p>
                  </div>
                  <el-button size="small" type="primary" @click="showLinkageDialog = true">
                    <el-icon><Connection /></el-icon> 配置联动
                  </el-button>
                  <el-button size="small" @click="showLinkageVisualEditor = true">
                    <el-icon><Share /></el-icon> 可视化编辑
                  </el-button>
                </div>
                
                <div class="property-section">
                  <div class="property-title">快速添加联动</div>
                  <el-form label-position="top" size="small">
                    <el-form-item label="联动类型">
                      <el-select v-model="quickLinkage.type">
                        <el-option label="数据筛选" value="filter" />
                        <el-option label="高亮显示" value="highlight" />
                        <el-option label="下钻分析" value="drill-down" />
                        <el-option label="同步缩放" value="sync-zoom" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="触发条件">
                      <el-select v-model="quickLinkage.trigger">
                        <el-option label="点击" value="click" />
                        <el-option label="悬停" value="hover" />
                        <el-option label="选择" value="select" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="目标图表">
                      <el-select v-model="quickLinkage.targets" multiple placeholder="选择目标">
                        <el-option
                          v-for="comp in store.canvasComponents.filter(c => c.id !== store.activeComponent?.id)"
                          :key="comp.id"
                          :label="comp.props.title || comp.type"
                          :value="comp.id"
                        />
                      </el-select>
                    </el-form-item>
                    <el-button type="primary" size="small" @click="handleQuickAddLinkage">
                      添加联动规则
                    </el-button>
                  </el-form>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="数据" name="data">
                <div class="property-section">
                  <div class="property-title">数据绑定</div>
                  <el-form label-position="top" size="small">
                    <el-form-item label="数据源类型">
                      <el-select
                        :model-value="store.activeComponent.dataBinding?.sourceType || 'static'"
                        @change="(val) => updateDataBinding('sourceType', val)"
                      >
                        <el-option label="静态数据" value="static" />
                        <el-option label="API接口" value="api" />
                        <el-option label="变量" value="variable" />
                      </el-select>
                    </el-form-item>
                    <el-form-item v-if="store.activeComponent.dataBinding?.sourceType === 'api'" label="数据源">
                      <el-select
                        :model-value="store.activeComponent.dataBinding?.source"
                        @change="(val) => updateDataBinding('source', val)"
                      >
                        <el-option
                          v-for="ds in store.dataSources"
                          :key="ds.id"
                          :label="ds.name"
                          :value="ds.id"
                        />
                      </el-select>
                    </el-form-item>
                    <el-form-item v-if="store.activeComponent.dataBinding?.sourceType === 'api'" label="刷新间隔(秒)">
                      <el-input-number
                        :model-value="store.activeComponent.dataBinding?.refreshInterval"
                        :min="0"
                        @change="(val) => updateDataBinding('refreshInterval', val)"
                      />
                    </el-form-item>
                  </el-form>
                </div>
              </el-tab-pane>
            </el-tabs>
            
            <div class="component-actions">
              <el-button-group>
                <el-tooltip content="置顶">
                  <el-button :icon="Top" size="small" @click="store.changeZIndex(store.activeComponent!.id, 'top')" />
                </el-tooltip>
                <el-tooltip content="上移一层">
                  <el-button :icon="CaretTop" size="small" @click="store.changeZIndex(store.activeComponent!.id, 'up')" />
                </el-tooltip>
                <el-tooltip content="下移一层">
                  <el-button :icon="CaretBottom" size="small" @click="store.changeZIndex(store.activeComponent!.id, 'down')" />
                </el-tooltip>
                <el-tooltip content="置底">
                  <el-button :icon="Bottom" size="small" @click="store.changeZIndex(store.activeComponent!.id, 'bottom')" />
                </el-tooltip>
              </el-button-group>
              
              <el-button-group>
                <el-tooltip :content="store.activeComponent.locked ? '解锁' : '锁定'">
                  <el-button
                    :icon="store.activeComponent.locked ? Unlock : Lock"
                    size="small"
                    @click="store.toggleLock(store.activeComponent!.id)"
                  />
                </el-tooltip>
                <el-tooltip :content="store.activeComponent.visible ? '隐藏' : '显示'">
                  <el-button
                    :icon="store.activeComponent.visible ? View : Hide"
                    size="small"
                    @click="store.toggleVisibility(store.activeComponent!.id)"
                  />
                </el-tooltip>
                <el-tooltip content="复制">
                  <el-button :icon="CopyDocument" size="small" @click="store.duplicateComponents([store.activeComponent!.id])" />
                </el-tooltip>
                <el-tooltip content="删除">
                  <el-button :icon="Delete" size="small" type="danger" @click="store.removeSelectedComponents()" />
                </el-tooltip>
              </el-button-group>
            </div>
          </template>
          
          <template v-else-if="store.selectedComponentIds.length > 1">
            <div class="multi-select-info">
              <p>已选中 {{ store.selectedComponentIds.length }} 个组件</p>
              <div class="align-buttons">
                <div class="align-row">
                  <el-tooltip content="左对齐">
                    <el-button size="small" @click="store.alignComponents('left')">
                      <el-icon><DArrowLeft /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="水平居中">
                    <el-button size="small" @click="store.alignComponents('center')">⫿</el-button>
                  </el-tooltip>
                  <el-tooltip content="右对齐">
                    <el-button size="small" @click="store.alignComponents('right')">
                      <el-icon><DArrowRight /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
                <div class="align-row">
                  <el-tooltip content="顶对齐">
                    <el-button size="small" @click="store.alignComponents('top')">
                      <el-icon><Top /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="垂直居中">
                    <el-button size="small" @click="store.alignComponents('middle')">⫾</el-button>
                  </el-tooltip>
                  <el-tooltip content="底对齐">
                    <el-button size="small" @click="store.alignComponents('bottom')">
                      <el-icon><Bottom /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
                <div class="align-row">
                  <el-tooltip content="水平分布">
                    <el-button size="small" @click="store.distributeComponents('horizontal')">⫼</el-button>
                  </el-tooltip>
                  <el-tooltip content="垂直分布">
                    <el-button size="small" @click="store.distributeComponents('vertical')">⫻</el-button>
                  </el-tooltip>
                </div>
              </div>
              <el-button type="danger" plain @click="store.removeSelectedComponents()">删除选中</el-button>
            </div>
          </template>
          
          <template v-else>
            <div class="no-selection">
              <el-empty description="请选择组件" :image-size="80" />
              
              <div class="canvas-settings">
                <div class="property-title">画布设置</div>
                <el-form label-position="top" size="small">
                  <el-form-item label="画布宽度">
                    <el-input-number
                      v-model="store.currentLayout.canvasWidth"
                      :min="800"
                      :max="3840"
                      :step="100"
                    />
                  </el-form-item>
                  <el-form-item label="画布高度">
                    <el-input-number
                      v-model="store.currentLayout.canvasHeight"
                      :min="600"
                      :max="2160"
                      :step="100"
                    />
                  </el-form-item>
                  <el-form-item label="网格大小">
                    <el-input-number
                      v-model="store.currentLayout.gridSize"
                      :min="5"
                      :max="50"
                      :step="5"
                    />
                  </el-form-item>
                  <el-form-item label="显示网格">
                    <el-switch v-model="store.currentLayout.showGrid" />
                  </el-form-item>
                  <el-form-item label="对齐网格">
                    <el-switch v-model="store.currentLayout.snapToGrid" />
                  </el-form-item>
                  <el-form-item label="背景色">
                    <el-color-picker v-model="store.currentLayout.backgroundColor" />
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </template>
        </template>
      </div>
    </div>
    
    <!-- 布局列表对话框 -->
    <el-dialog v-model="showLayoutDialog" title="加载布局" width="600px">
      <el-tabs>
        <el-tab-pane label="我的布局">
          <el-table :data="store.layouts" style="width: 100%">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="updatedAt" label="更新时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.updatedAt) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="handleLoadLayout(row.id)">加载</el-button>
                <el-button size="small" type="danger" @click="handleDeleteLayout(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="模板">
          <div class="template-grid">
            <div
              v-for="template in store.templates"
              :key="template.id"
              class="template-card"
              @click="handleLoadTemplate(template.id)"
            >
              <div class="template-preview">
                <el-icon :size="48"><Grid /></el-icon>
              </div>
              <div class="template-info">
                <div class="template-name">{{ template.name }}</div>
                <div class="template-desc">{{ template.description }}</div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
    
    <!-- 保存为模板对话框 -->
    <el-dialog v-model="showTemplateDialog" title="保存为模板" width="400px">
      <el-form :model="templateForm" label-width="80px">
        <el-form-item label="模板名称">
          <el-input v-model="templateForm.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="templateForm.description" type="textarea" :rows="3" placeholder="请输入模板描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTemplateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveAsTemplate">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 分享对话框 -->
    <el-dialog v-model="showShareDialog" title="分享布局" width="400px">
      <div class="share-content">
        <p>分享链接：</p>
        <el-input v-model="shareInfo.url" readonly>
          <template #append>
            <el-button @click="copyShareLink">复制</el-button>
          </template>
        </el-input>
        <p style="margin-top: 16px">访问码：<strong>{{ shareInfo.code }}</strong></p>
      </div>
    </el-dialog>
    
    <!-- 预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      title="预览"
      fullscreen
      :show-close="true"
    >
      <div class="preview-container">
        <div
          class="preview-canvas"
          :style="{
            width: store.currentLayout.canvasWidth + 'px',
            height: store.currentLayout.canvasHeight + 'px',
            backgroundColor: store.currentLayout.backgroundColor,
          }"
        >
          <div
            v-for="comp in store.canvasComponents"
            :key="comp.id"
            :style="getComponentStyle(comp)"
            style="position: absolute"
          >
            <component
              :is="getComponentRenderer(comp.type)"
              v-bind="comp.props"
              :style="getComponentInnerStyle(comp)"
            />
          </div>
        </div>
      </div>
    </el-dialog>
    
    <!-- 联动配置对话框 -->
    <el-dialog
      v-model="showLinkageDialog"
      title="联动配置"
      width="800px"
      :destroy-on-close="false"
    >
      <LinkageConfigPanel />
    </el-dialog>
    
    <!-- 可视化联动编辑器对话框 -->
    <el-dialog
      v-model="showLinkageVisualEditor"
      title="可视化联动编辑"
      width="90%"
      fullscreen
      :destroy-on-close="false"
    >
      <LinkageVisualEditor style="height: calc(100vh - 120px)" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, markRaw } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  FolderOpened, DocumentAdd, Files, View, Download, Share,
  RefreshLeft, RefreshRight, Delete, Search, Lock, Unlock,
  Top, Bottom, CaretTop, CaretBottom, CopyDocument, Hide, Grid,
  DArrowLeft, DArrowRight, Connection,
} from '@element-plus/icons-vue';
import LinkageConfigPanel from '@/components/bindage/LinkageConfigPanel.vue';
import LinkageVisualEditor from '@/components/bindage/LinkageVisualEditor.vue';
import { useVisualizationStore } from '@/store/visualization';
import { useLinkageStore } from '@/store/bindage';
import type { LinkageType, TriggerType } from '@/api/bindage';
import type { ComponentType, CanvasComponent, ComponentDefinition } from '@/api/visualization';

// 导入图表组件
import BarChart from '@/components/charts/BarChart.vue';
import LineChart from '@/components/charts/LineChart.vue';
import PieChart from '@/components/charts/PieChart.vue';
import ScatterChart from '@/components/charts/ScatterChart.vue';
import HeatmapChart from '@/components/charts/HeatmapChart.vue';
import MapChart from '@/components/charts/MapChart.vue';
import RadarChart from '@/components/charts/RadarChart.vue';
import GaugeChart from '@/components/charts/GaugeChart.vue';
import TitleComponent from '@/components/charts/TitleComponent.vue';
import TextBox from '@/components/charts/TextBox.vue';
import MetricCard from '@/components/charts/MetricCard.vue';
import FilterComponent from '@/components/charts/FilterComponent.vue';
import DatePickerComponent from '@/components/charts/DatePickerComponent.vue';
import DropdownComponent from '@/components/charts/DropdownComponent.vue';
import SearchBox from '@/components/charts/SearchBox.vue';
import ContainerComponent from '@/components/charts/ContainerComponent.vue';

const store = useVisualizationStore();
const linkageStore = useLinkageStore();

// 组件映射
const componentMap: Record<ComponentType, any> = {
  'bar-chart': markRaw(BarChart),
  'line-chart': markRaw(LineChart),
  'pie-chart': markRaw(PieChart),
  'scatter-chart': markRaw(ScatterChart),
  'heatmap-chart': markRaw(HeatmapChart),
  'map-chart': markRaw(MapChart),
  'radar-chart': markRaw(RadarChart),
  'gauge-chart': markRaw(GaugeChart),
  'title': markRaw(TitleComponent),
  'text-box': markRaw(TextBox),
  'metric-card': markRaw(MetricCard),
  'filter': markRaw(FilterComponent),
  'date-picker': markRaw(DatePickerComponent),
  'dropdown': markRaw(DropdownComponent),
  'search-box': markRaw(SearchBox),
  'container': markRaw(ContainerComponent),
  'row-layout': markRaw(ContainerComponent),
  'column-layout': markRaw(ContainerComponent),
  'tabs': markRaw(ContainerComponent),
};

// Refs
const canvasContainerRef = ref<HTMLElement | null>(null);
const canvasRef = ref<HTMLElement | null>(null);

// State
const zoomPercent = ref(100);
const activePropertyTab = ref('props');
const showLayoutDialog = ref(false);
const showTemplateDialog = ref(false);
const showShareDialog = ref(false);
const showPreviewDialog = ref(false);
const templateForm = ref({ name: '', description: '' });
const shareInfo = ref({ url: '', code: '' });
const showLinkageDialog = ref(false);
const showLinkageVisualEditor = ref(false);
const quickLinkage = ref({
  type: 'filter' as LinkageType,
  trigger: 'click' as TriggerType,
  targets: [] as string[],
});

// 拖拽相关
const draggedComponent = ref<ComponentDefinition | null>(null);
const dragStartPos = ref({ x: 0, y: 0 });
const componentStartPos = ref({ x: 0, y: 0 });
const resizeStartSize = ref({ width: 0, height: 0 });
const resizeDirection = ref('');
const selectionBox = ref<{ x: number; y: number; width: number; height: number } | null>(null);

// Computed
const canvasStyle = computed(() => ({
  width: `${store.currentLayout.canvasWidth}px`,
  height: `${store.currentLayout.canvasHeight}px`,
  backgroundColor: store.currentLayout.backgroundColor,
  transform: `scale(${store.canvasScale})`,
  transformOrigin: 'top left',
}));

const gridStyle = computed(() => ({
  backgroundSize: `${store.currentLayout.gridSize}px ${store.currentLayout.gridSize}px`,
}));

const selectionBoxStyle = computed(() => {
  if (!selectionBox.value) return {};
  return {
    left: `${selectionBox.value.x}px`,
    top: `${selectionBox.value.y}px`,
    width: `${selectionBox.value.width}px`,
    height: `${selectionBox.value.height}px`,
  };
});

// Methods
function getComponentRenderer(type: ComponentType) {
  return componentMap[type] || ContainerComponent;
}

function getComponentStyle(comp: CanvasComponent) {
  return {
    left: `${comp.x}px`,
    top: `${comp.y}px`,
    width: `${comp.width}px`,
    height: `${comp.height}px`,
    zIndex: comp.zIndex,
    opacity: comp.visible ? (comp.styles.opacity ?? 1) : 0.3,
  };
}

function getComponentInnerStyle(comp: CanvasComponent) {
  return {
    width: '100%',
    height: '100%',
    backgroundColor: comp.styles.backgroundColor,
    borderColor: comp.styles.borderColor,
    borderWidth: `${comp.styles.borderWidth || 0}px`,
    borderStyle: comp.styles.borderWidth ? 'solid' : 'none',
    borderRadius: `${comp.styles.borderRadius || 0}px`,
    padding: typeof comp.styles.padding === 'number' ? `${comp.styles.padding}px` : undefined,
  };
}

function handleDragStart(event: DragEvent, comp: ComponentDefinition) {
  draggedComponent.value = comp;
  event.dataTransfer?.setData('text/plain', comp.type);
}

function handleDrop(event: DragEvent) {
  if (!draggedComponent.value || !canvasRef.value) return;
  
  const rect = canvasRef.value.getBoundingClientRect();
  const x = (event.clientX - rect.left) / store.canvasScale;
  const y = (event.clientY - rect.top) / store.canvasScale;
  
  store.addComponent(draggedComponent.value.type, { x, y });
  draggedComponent.value = null;
}

function handleAddComponent(type: ComponentType) {
  store.addComponent(type, { x: 100, y: 100 });
}

function handleCanvasClick(event: MouseEvent) {
  if (event.target === canvasRef.value || (event.target as HTMLElement).classList.contains('canvas-grid')) {
    store.clearSelection();
  }
}

function handleComponentClick(event: MouseEvent, comp: CanvasComponent) {
  store.selectComponent(comp.id, event.ctrlKey || event.metaKey);
}

function handleComponentMouseDown(event: MouseEvent, comp: CanvasComponent) {
  if (comp.locked) return;
  
  if (!store.selectedComponentIds.includes(comp.id)) {
    store.selectComponent(comp.id, event.ctrlKey || event.metaKey);
  }
  
  store.isDragging = true;
  dragStartPos.value = { x: event.clientX, y: event.clientY };
  componentStartPos.value = { x: comp.x, y: comp.y };
  
  const handleMouseMove = (e: MouseEvent) => {
    const dx = (e.clientX - dragStartPos.value.x) / store.canvasScale;
    const dy = (e.clientY - dragStartPos.value.y) / store.canvasScale;
    
    store.selectedComponents.forEach(c => {
      if (!c.locked) {
        const startX = c.id === comp.id ? componentStartPos.value.x : c.x;
        const startY = c.id === comp.id ? componentStartPos.value.y : c.y;
        store.moveComponent(c.id, startX + dx, startY + dy);
      }
    });
  };
  
  const handleMouseUp = () => {
    store.isDragging = false;
    if (dragStartPos.value.x !== event.clientX || dragStartPos.value.y !== event.clientY) {
      store.saveToHistory('移动组件');
    }
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
  
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
}

function handleResizeStart(event: MouseEvent, comp: CanvasComponent, direction: string) {
  store.isResizing = true;
  resizeDirection.value = direction;
  dragStartPos.value = { x: event.clientX, y: event.clientY };
  componentStartPos.value = { x: comp.x, y: comp.y };
  resizeStartSize.value = { width: comp.width, height: comp.height };
  
  const handleMouseMove = (e: MouseEvent) => {
    const dx = (e.clientX - dragStartPos.value.x) / store.canvasScale;
    const dy = (e.clientY - dragStartPos.value.y) / store.canvasScale;
    
    let newWidth = resizeStartSize.value.width;
    let newHeight = resizeStartSize.value.height;
    let newX = componentStartPos.value.x;
    let newY = componentStartPos.value.y;
    
    if (direction.includes('e')) newWidth += dx;
    if (direction.includes('w')) { newWidth -= dx; newX += dx; }
    if (direction.includes('s')) newHeight += dy;
    if (direction.includes('n')) { newHeight -= dy; newY += dy; }
    
    if (newWidth > 50 && newHeight > 50) {
      store.updateComponent(comp.id, { x: newX, y: newY });
      store.resizeComponent(comp.id, newWidth, newHeight);
    }
  };
  
  const handleMouseUp = () => {
    store.isResizing = false;
    store.saveToHistory('调整大小');
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
  
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
}

function updateComponentProp(prop: string, value: any) {
  if (!store.activeComponent) return;
  store.updateComponentWithHistory(store.activeComponent.id, { [prop]: value }, `修改${prop}`);
}

function updateComponentProps(key: string, value: any) {
  if (!store.activeComponent) return;
  store.updateComponentProps(store.activeComponent.id, { [key]: value });
}

function updateComponentPropsJson(key: string, value: string) {
  if (!store.activeComponent) return;
  try {
    const parsed = JSON.parse(value);
    store.updateComponentProps(store.activeComponent.id, { [key]: parsed });
  } catch {
    // 忽略无效JSON
  }
}

function updateComponentStyle(key: string, value: any) {
  if (!store.activeComponent) return;
  store.updateComponentStyles(store.activeComponent.id, { [key]: value });
}

function updateDataBinding(key: string, value: any) {
  if (!store.activeComponent) return;
  const binding = { ...store.activeComponent.dataBinding, [key]: value };
  store.updateComponentDataBinding(store.activeComponent.id, binding as any);
}

function handleZoomChange(value: number) {
  store.setCanvasScale(value / 100);
}

function handleFitToCanvas() {
  if (!canvasContainerRef.value) return;
  const { clientWidth, clientHeight } = canvasContainerRef.value;
  store.fitToCanvas(clientWidth - 40, clientHeight - 40);
  zoomPercent.value = Math.round(store.canvasScale * 100);
}

async function handleSave() {
  try {
    await store.saveCurrentLayout();
    ElMessage.success('保存成功');
  } catch {
    ElMessage.warning('保存失败');
  }
}

async function handleLoadLayout(id: string) {
  if (store.hasUnsavedChanges) {
    await ElMessageBox.confirm('当前布局有未保存的更改，是否继续？', '提示', {
      confirmButtonText: '继续',
      cancelButtonText: '取消',
      type: 'warning',
    });
  }
  await store.loadLayout(id);
  showLayoutDialog.value = false;
  ElMessage.success('加载成功');
}

async function handleLoadTemplate(id: string) {
  if (store.hasUnsavedChanges) {
    await ElMessageBox.confirm('当前布局有未保存的更改，是否继续？', '提示', {
      confirmButtonText: '继续',
      cancelButtonText: '取消',
      type: 'warning',
    });
  }
  await store.createLayoutFromTemplate(id);
  showLayoutDialog.value = false;
  ElMessage.success('从模板创建成功');
}

async function handleDeleteLayout(id: string) {
  await ElMessageBox.confirm('确定要删除此布局吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  });
  await store.removeLayout(id);
  ElMessage.success('删除成功');
}

async function handleSaveAsTemplate() {
  if (!templateForm.value.name) {
    ElMessage.warning('请输入模板名称');
    return;
  }
  await store.saveCurrentAsTemplate(templateForm.value.name, templateForm.value.description);
  showTemplateDialog.value = false;
  templateForm.value = { name: '', description: '' };
  ElMessage.success('保存模板成功');
}

function handlePreview() {
  showPreviewDialog.value = true;
}

async function handleExport() {
  await store.exportCurrentLayout();
  ElMessage.success('导出成功');
}

async function handleShare() {
  try {
    const result = await store.shareLayout();
    shareInfo.value = result;
    showShareDialog.value = true;
  } catch {
    ElMessage.warning('生成分享链接失败');
  }
}

function copyShareLink() {
  navigator.clipboard.writeText(shareInfo.value.url);
  ElMessage.success('链接已复制');
}

async function handleClearCanvas() {
  await ElMessageBox.confirm('确定要清空画布吗？此操作不可恢复。', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  });
  store.clearCanvas();
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN');
}

function getComponentLinkageInfo(componentId: string) {
  const linkages = linkageStore.getComponentLinkages(componentId);
  return {
    asSource: linkages.asSource.length,
    asTarget: linkages.asTarget.length,
  };
}

function handleQuickAddLinkage() {
  if (!store.activeComponent || quickLinkage.value.targets.length === 0) {
    ElMessage.warning('请选择目标图表');
    return;
  }
  
  const rule = linkageStore.addRule(store.activeComponent.id);
  linkageStore.updateRule(rule.id, {
    name: `${store.activeComponent.props.title || store.activeComponent.type} 联动`,
    targetType: 'specific',
    targetComponentIds: quickLinkage.value.targets,
    linkageType: quickLinkage.value.type,
    triggerType: quickLinkage.value.trigger,
  });
  
  ElMessage.success('联动规则已添加');
  quickLinkage.value.targets = [];
}

// 键盘快捷键
function handleKeyDown(event: KeyboardEvent) {
  const isCtrl = event.ctrlKey || event.metaKey;
  
  if (isCtrl && event.key === 'z') {
    event.preventDefault();
    if (event.shiftKey) {
      store.redo();
    } else {
      store.undo();
    }
  } else if (isCtrl && event.key === 'c') {
    event.preventDefault();
    store.copySelectedComponents();
  } else if (isCtrl && event.key === 'x') {
    event.preventDefault();
    store.cutSelectedComponents();
  } else if (isCtrl && event.key === 'v') {
    event.preventDefault();
    store.pasteComponents();
  } else if (isCtrl && event.key === 'a') {
    event.preventDefault();
    store.selectAllComponents();
  } else if (isCtrl && event.key === 's') {
    event.preventDefault();
    handleSave();
  } else if (event.key === 'Delete' || event.key === 'Backspace') {
    if (store.selectedComponentIds.length > 0) {
      store.removeSelectedComponents();
    }
  } else if (event.key === 'Escape') {
    store.clearSelection();
  }
}

onMounted(() => {
  store.initialize();
  document.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown);
});
</script>

<style scoped lang="scss">
.visualization-workbench {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  
  .toolbar-left, .toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .toolbar-center {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .layout-name-input {
      width: 200px;
    }
  }
  
  .zoom-label {
    font-size: 13px;
    color: #606266;
  }
}

.workbench-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.component-panel, .property-panel {
  width: 280px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  
  &.collapsed {
    width: 40px;
  }
}

.property-panel {
  border-right: none;
  border-left: 1px solid #e4e7ed;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  font-weight: 500;
  border-bottom: 1px solid #e4e7ed;
}

.panel-search {
  padding: 12px;
}

.category-tabs {
  padding: 0 12px 12px;
  
  .el-radio-group {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
}

.component-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  align-content: start;
}

.component-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  background: #f5f7fa;
  border-radius: 8px;
  cursor: grab;
  transition: all 0.2s;
  
  &:hover {
    background: #ecf5ff;
    transform: translateY(-2px);
  }
  
  &:active {
    cursor: grabbing;
  }
  
  .component-name {
    font-size: 12px;
    color: #606266;
    text-align: center;
  }
}

.canvas-container {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background: #e8e8e8;
}

.canvas {
  position: relative;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.canvas-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(to right, #ddd 1px, transparent 1px),
    linear-gradient(to bottom, #ddd 1px, transparent 1px);
  pointer-events: none;
}

.canvas-component {
  position: absolute;
  cursor: move;
  box-sizing: border-box;
  
  &.selected {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }
  
  &.locked {
    cursor: not-allowed;
  }
  
  &.hidden {
    pointer-events: none;
  }
}

.resize-handle {
  position: absolute;
  width: 10px;
  height: 10px;
  background: var(--color-primary);
  border: 2px solid #fff;
  border-radius: 2px;
  
  &.nw { top: -5px; left: -5px; cursor: nw-resize; }
  &.ne { top: -5px; right: -5px; cursor: ne-resize; }
  &.sw { bottom: -5px; left: -5px; cursor: sw-resize; }
  &.se { bottom: -5px; right: -5px; cursor: se-resize; }
  &.n { top: -5px; left: 50%; transform: translateX(-50%); cursor: n-resize; }
  &.s { bottom: -5px; left: 50%; transform: translateX(-50%); cursor: s-resize; }
  &.w { left: -5px; top: 50%; transform: translateY(-50%); cursor: w-resize; }
  &.e { right: -5px; top: 50%; transform: translateY(-50%); cursor: e-resize; }
}

.lock-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
  color: var(--color-text-secondary);
}

.selection-box {
  position: absolute;
  border: 1px dashed var(--color-primary);
  background: rgba(64, 158, 255, 0.1);
  pointer-events: none;
}

.property-section {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.property-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 12px;
}

.component-actions {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid #e4e7ed;
}

.multi-select-info {
  padding: 16px;
  text-align: center;
  
  .align-buttons {
    margin: 16px 0;
  }
  
  .align-row {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-bottom: 8px;
  }
}

.no-selection {
  padding: 16px;
}

.canvas-settings {
  margin-top: 24px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.template-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    border-color: var(--color-primary);
    box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
  }
  
  .template-preview {
    height: 100px;
    background: #f5f7fa;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #c0c4cc;
  }
  
  .template-info {
    padding: 12px;
    
    .template-name {
      font-weight: 500;
      margin-bottom: 4px;
    }
    
    .template-desc {
      font-size: 12px;
      color: var(--color-text-secondary);
    }
  }
}

.share-content {
  p {
    margin-bottom: 8px;
    color: #606266;
  }
}

.preview-container {
  width: 100%;
  height: calc(100vh - 120px);
  overflow: auto;
  display: flex;
  justify-content: center;
  padding: 20px;
  background: #e8e8e8;
}

.preview-canvas {
  position: relative;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.linkage-summary {
  margin-bottom: 12px;
  
  p {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    font-size: 13px;
    color: #606266;
  }
  
  .no-linkage {
    color: var(--color-text-secondary);
    font-style: italic;
  }
}
</style>
