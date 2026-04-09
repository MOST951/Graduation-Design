<template>
  <div class="linkage-config-panel">
    <div class="panel-header">
      <h3>联动配置</h3>
      <div class="header-actions">
        <el-switch
          v-model="linkageStore.config.globalEnabled"
          active-text="启用"
          inactive-text="禁用"
          @change="handleGlobalToggle"
        />
      </div>
    </div>
    
    <el-tabs v-model="activeTab">
      <!-- 联动规则 -->
      <el-tab-pane label="联动规则" name="rules">
        <div class="rules-toolbar">
          <el-button type="primary" size="small" :icon="Plus" @click="handleAddRule">
            添加规则
          </el-button>
          <el-button size="small" :icon="Download" @click="handleExport">导出</el-button>
          <el-button size="small" :icon="Upload" @click="handleImport">导入</el-button>
        </div>
        
        <div class="rules-list">
          <el-collapse v-model="expandedRules">
            <el-collapse-item
              v-for="rule in linkageStore.rules"
              :key="rule.id"
              :name="rule.id"
            >
              <template #title>
                <div class="rule-header">
                  <el-switch
                    v-model="rule.enabled"
                    size="small"
                    @click.stop
                    @change="() => linkageStore.updateRule(rule.id, { enabled: rule.enabled })"
                  />
                  <span class="rule-name">{{ rule.name }}</span>
                  <el-tag size="small" :type="getLinkageTypeTag(rule.linkageType)">
                    {{ getLinkageTypeName(rule.linkageType) }}
                  </el-tag>
                  <el-tag size="small" type="info">
                    {{ getTriggerTypeName(rule.triggerType) }}
                  </el-tag>
                </div>
              </template>
              
              <div class="rule-content">
                <el-form label-position="top" size="small">
                  <el-form-item label="规则名称">
                    <el-input
                      v-model="rule.name"
                      @change="() => linkageStore.updateRule(rule.id, { name: rule.name })"
                    />
                  </el-form-item>
                  
                  <el-row :gutter="12">
                    <el-col :span="12">
                      <el-form-item label="源组件">
                        <el-select
                          v-model="rule.sourceComponentId"
                          placeholder="选择源组件"
                          @change="() => linkageStore.updateRule(rule.id, { sourceComponentId: rule.sourceComponentId })"
                        >
                          <el-option
                            v-for="comp in availableComponents"
                            :key="comp.id"
                            :label="comp.name"
                            :value="comp.id"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="源字段">
                        <el-input
                          v-model="rule.sourceField"
                          placeholder="可选"
                          @change="() => linkageStore.updateRule(rule.id, { sourceField: rule.sourceField })"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <el-row :gutter="12">
                    <el-col :span="12">
                      <el-form-item label="联动类型">
                        <el-select
                          v-model="rule.linkageType"
                          @change="() => linkageStore.updateRule(rule.id, { linkageType: rule.linkageType })"
                        >
                          <el-option label="数据筛选" value="filter" />
                          <el-option label="高亮显示" value="highlight" />
                          <el-option label="下钻分析" value="drill-down" />
                          <el-option label="同步缩放" value="sync-zoom" />
                          <el-option label="同步选择" value="sync-selection" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="触发条件">
                        <el-select
                          v-model="rule.triggerType"
                          @change="() => linkageStore.updateRule(rule.id, { triggerType: rule.triggerType })"
                        >
                          <el-option label="点击" value="click" />
                          <el-option label="悬停" value="hover" />
                          <el-option label="选择" value="select" />
                          <el-option label="框选" value="brush" />
                          <el-option label="缩放" value="zoom" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <el-form-item label="目标类型">
                    <el-radio-group
                      v-model="rule.targetType"
                      @change="() => linkageStore.updateRule(rule.id, { targetType: rule.targetType })"
                    >
                      <el-radio label="all">所有图表</el-radio>
                      <el-radio label="specific">指定图表</el-radio>
                      <el-radio label="group">联动组</el-radio>
                    </el-radio-group>
                  </el-form-item>
                  
                  <el-form-item v-if="rule.targetType === 'specific'" label="目标组件">
                    <el-select
                      v-model="rule.targetComponentIds"
                      multiple
                      placeholder="选择目标组件"
                      @change="() => linkageStore.updateRule(rule.id, { targetComponentIds: rule.targetComponentIds })"
                    >
                      <el-option
                        v-for="comp in availableComponents.filter(c => c.id !== rule.sourceComponentId)"
                        :key="comp.id"
                        :label="comp.name"
                        :value="comp.id"
                      />
                    </el-select>
                  </el-form-item>
                  
                  <el-form-item v-if="rule.targetType === 'group'" label="联动组">
                    <el-select
                      v-model="rule.targetGroup"
                      placeholder="选择联动组"
                      @change="() => linkageStore.updateRule(rule.id, { targetGroup: rule.targetGroup })"
                    >
                      <el-option
                        v-for="group in linkageStore.groups"
                        :key="group.id"
                        :label="group.name"
                        :value="group.id"
                      />
                    </el-select>
                  </el-form-item>
                  
                  <el-form-item label="联动方向">
                    <el-radio-group
                      v-model="rule.direction"
                      @change="() => linkageStore.updateRule(rule.id, { direction: rule.direction })"
                    >
                      <el-radio label="one-way">单向联动</el-radio>
                      <el-radio label="two-way">双向联动</el-radio>
                    </el-radio-group>
                  </el-form-item>
                  
                  <el-row :gutter="12">
                    <el-col :span="12">
                      <el-form-item label="延迟(ms)">
                        <el-input-number
                          v-model="rule.delay"
                          :min="0"
                          :max="5000"
                          :step="100"
                          @change="() => linkageStore.updateRule(rule.id, { delay: rule.delay })"
                        />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="优先级">
                        <el-input-number
                          v-model="rule.priority"
                          :min="0"
                          :max="100"
                          @change="() => linkageStore.updateRule(rule.id, { priority: rule.priority })"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  
                  <!-- 条件配置 -->
                  <el-form-item label="触发条件">
                    <div class="conditions-list">
                      <div
                        v-for="(condition, index) in rule.conditions"
                        :key="index"
                        class="condition-item"
                      >
                        <el-input
                          v-model="condition.field"
                          placeholder="字段"
                          style="width: 100px"
                        />
                        <el-select v-model="condition.operator" style="width: 100px">
                          <el-option label="等于" value="equals" />
                          <el-option label="包含" value="contains" />
                          <el-option label="大于" value="greater" />
                          <el-option label="小于" value="less" />
                          <el-option label="介于" value="between" />
                          <el-option label="在列表中" value="in" />
                        </el-select>
                        <el-input
                          v-model="condition.value"
                          placeholder="值"
                          style="width: 100px"
                        />
                        <el-switch v-model="condition.enabled" size="small" />
                        <el-button
                          :icon="Delete"
                          size="small"
                          type="danger"
                          text
                          @click="removeCondition(rule, index)"
                        />
                      </div>
                      <el-button size="small" :icon="Plus" @click="addCondition(rule)">
                        添加条件
                      </el-button>
                    </div>
                  </el-form-item>
                  
                  <!-- 链式联动 -->
                  <el-form-item label="链式联动">
                    <el-select
                      v-model="rule.chainRules"
                      multiple
                      placeholder="选择后续规则"
                      @change="() => linkageStore.updateRule(rule.id, { chainRules: rule.chainRules })"
                    >
                      <el-option
                        v-for="r in linkageStore.rules.filter(r => r.id !== rule.id)"
                        :key="r.id"
                        :label="r.name"
                        :value="r.id"
                      />
                    </el-select>
                  </el-form-item>
                  
                  <!-- 数据转换 -->
                  <el-form-item label="数据转换表达式">
                    <el-input
                      v-model="rule.transform"
                      placeholder="例如: value.name 或 value * 100"
                      @change="() => linkageStore.updateRule(rule.id, { transform: rule.transform })"
                    />
                  </el-form-item>
                </el-form>
                
                <div class="rule-actions">
                  <el-button size="small" @click="handlePreviewRule(rule)">
                    <el-icon><View /></el-icon> 预览效果
                  </el-button>
                  <el-button size="small" @click="linkageStore.duplicateRule(rule.id)">
                    <el-icon><CopyDocument /></el-icon> 复制
                  </el-button>
                  <el-button size="small" type="danger" @click="handleDeleteRule(rule.id)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-button>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
          
          <el-empty v-if="linkageStore.rules.length === 0" description="暂无联动规则" />
        </div>
      </el-tab-pane>
      
      <!-- 联动组 -->
      <el-tab-pane label="联动组" name="groups">
        <div class="groups-toolbar">
          <el-button type="primary" size="small" :icon="Plus" @click="handleAddGroup">
            添加联动组
          </el-button>
        </div>
        
        <div class="groups-list">
          <div
            v-for="group in linkageStore.groups"
            :key="group.id"
            class="group-item"
          >
            <div class="group-header">
              <div class="group-color" :style="{ backgroundColor: group.color }"></div>
              <el-input
                v-model="group.name"
                size="small"
                @change="() => linkageStore.updateGroup(group.id, { name: group.name })"
              />
              <el-color-picker
                v-model="group.color"
                size="small"
                @change="() => linkageStore.updateGroup(group.id, { color: group.color })"
              />
              <el-button
                :icon="Delete"
                size="small"
                type="danger"
                text
                @click="linkageStore.removeGroup(group.id)"
              />
            </div>
            <div class="group-components">
              <el-select
                v-model="group.componentIds"
                multiple
                placeholder="选择组件"
                size="small"
                @change="() => linkageStore.updateGroup(group.id, { componentIds: group.componentIds })"
              >
                <el-option
                  v-for="comp in availableComponents"
                  :key="comp.id"
                  :label="comp.name"
                  :value="comp.id"
                />
              </el-select>
            </div>
          </div>
          
          <el-empty v-if="linkageStore.groups.length === 0" description="暂无联动组" />
        </div>
      </el-tab-pane>
      
      <!-- 联动状态 -->
      <el-tab-pane label="当前状态" name="state">
        <div class="state-panel">
          <div class="state-section">
            <h4>活跃规则</h4>
            <div class="active-rules">
              <el-tag
                v-for="ruleId in linkageStore.state.activeRules"
                :key="ruleId"
                closable
                @close="handleDeactivateRule(ruleId)"
              >
                {{ getRuleName(ruleId) }}
              </el-tag>
              <span v-if="linkageStore.state.activeRules.length === 0" class="no-data">
                暂无活跃规则
              </span>
            </div>
          </div>
          
          <div class="state-section">
            <h4>当前筛选</h4>
            <div class="filters-list">
              <div
                v-for="(filter, key) in linkageStore.activeFilters"
                :key="key"
                class="filter-item"
              >
                <span>{{ filter.field || '默认' }}: {{ JSON.stringify(filter.value) }}</span>
                <el-button size="small" text @click="linkageStore.clearFilter(String(key))">
                  清除
                </el-button>
              </div>
              <span v-if="Object.keys(linkageStore.activeFilters).length === 0" class="no-data">
                暂无筛选条件
              </span>
            </div>
          </div>
          
          <div class="state-section">
            <h4>下钻路径</h4>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item @click="linkageStore.resetDrill()">根级</el-breadcrumb-item>
              <el-breadcrumb-item
                v-for="(item, index) in linkageStore.drillPath"
                :key="index"
              >
                {{ JSON.stringify(item.data).substring(0, 20) }}...
              </el-breadcrumb-item>
            </el-breadcrumb>
            <el-button
              v-if="linkageStore.drillPath.length > 0"
              size="small"
              @click="linkageStore.drillUp()"
            >
              返回上一级
            </el-button>
          </div>
          
          <div class="state-actions">
            <el-button @click="linkageStore.resetState()">重置所有状态</el-button>
            <el-button @click="linkageStore.restoreAllTemporarilyDisabled()">
              恢复临时禁用
            </el-button>
          </div>
        </div>
      </el-tab-pane>
      
      <!-- 历史记录 -->
      <el-tab-pane label="历史记录" name="history">
        <div class="history-panel">
          <div class="history-actions">
            <el-button
              :disabled="!linkageStore.canUndo"
              :icon="RefreshLeft"
              @click="linkageStore.undo()"
            >
              撤销
            </el-button>
            <el-button
              :disabled="!linkageStore.canRedo"
              :icon="RefreshRight"
              @click="linkageStore.redo()"
            >
              重做
            </el-button>
          </div>
          
          <el-timeline>
            <el-timeline-item
              v-for="(item, index) in linkageStore.history.slice().reverse()"
              :key="item.id"
              :timestamp="formatTime(item.timestamp)"
              :type="index === linkageStore.history.length - 1 - linkageStore.historyIndex ? 'primary' : 'info'"
            >
              <div class="history-item">
                <span>{{ getRuleName(item.event.ruleId) }}</span>
                <el-tag size="small">{{ item.event.triggerType }}</el-tag>
              </div>
            </el-timeline-item>
          </el-timeline>
          
          <el-empty v-if="linkageStore.history.length === 0" description="暂无历史记录" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
  Plus, Delete, Download, Upload, View, CopyDocument,
  RefreshLeft, RefreshRight,
} from '@element-plus/icons-vue';
import { useLinkageStore } from '@/store/bindage';
import { useVisualizationStore } from '@/store/visualization';
import {
  type LinkageRule,
  type LinkageType,
  type TriggerType,
  getLinkageTypeName,
  getTriggerTypeName,
} from '@/api/bindage';

const linkageStore = useLinkageStore();
const visualizationStore = useVisualizationStore();

const activeTab = ref('rules');
const expandedRules = ref<string[]>([]);

// 可用组件列表
const availableComponents = computed(() => {
  return visualizationStore.canvasComponents.map(comp => ({
    id: comp.id,
    name: comp.props.title || comp.type,
    type: comp.type,
  }));
});

function getLinkageTypeTag(type: LinkageType): '' | 'success' | 'warning' | 'info' | 'danger' {
  const tags: Record<LinkageType, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    'filter': '',
    'highlight': 'success',
    'drill-down': 'warning',
    'sync-zoom': 'info',
    'sync-selection': 'danger',
  };
  return tags[type] || '';
}

function getRuleName(ruleId: string): string {
  const rule = linkageStore.rules.find(r => r.id === ruleId);
  return rule?.name || ruleId;
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString('zh-CN');
}

function handleGlobalToggle(enabled: boolean) {
  linkageStore.setGlobalEnabled(enabled);
  ElMessage.success(enabled ? '联动已启用' : '联动已禁用');
}

function handleAddRule() {
  if (availableComponents.value.length === 0) {
    ElMessage.warning('请先添加图表组件');
    return;
  }
  const rule = linkageStore.addRule(availableComponents.value[0].id);
  expandedRules.value.push(rule.id);
}

function handleDeleteRule(ruleId: string) {
  ElMessageBox.confirm('确定要删除此规则吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    linkageStore.removeRule(ruleId);
    ElMessage.success('删除成功');
  });
}

function handlePreviewRule(rule: LinkageRule) {
  linkageStore.startPreview(rule);
  ElMessage.info('预览模式已开启，悬停在图表上查看效果');
  
  // 3秒后自动关闭预览
  setTimeout(() => {
    linkageStore.stopPreview();
  }, 3000);
}

function handleDeactivateRule(ruleId: string) {
  linkageStore.temporarilyDisableRule(ruleId);
  linkageStore.clearFilter();
  linkageStore.clearHighlight();
}

function addCondition(rule: LinkageRule) {
  if (!rule.conditions) {
    rule.conditions = [];
  }
  rule.conditions.push({
    field: '',
    operator: 'equals',
    value: '',
    enabled: true,
  });
  linkageStore.updateRule(rule.id, { conditions: rule.conditions });
}

function removeCondition(rule: LinkageRule, index: number) {
  rule.conditions.splice(index, 1);
  linkageStore.updateRule(rule.id, { conditions: rule.conditions });
}

function handleAddGroup() {
  linkageStore.addGroup('新建联动组');
}

function handleExport() {
  const json = linkageStore.exportConfig();
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'linkage-config.json';
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success('导出成功');
}

function handleImport() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = (e) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        linkageStore.importConfig(e.target?.result as string);
        ElMessage.success('导入成功');
      } catch {
        ElMessage.error('导入失败：无效的配置文件');
      }
    };
    reader.readAsText(file);
  };
  input.click();
}
</script>

<style scoped lang="scss">
.linkage-config-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  
  h3 {
    margin: 0;
    font-size: 16px;
  }
}

.rules-toolbar, .groups-toolbar {
  padding: 12px;
  display: flex;
  gap: 8px;
}

.rules-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.rule-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  
  .rule-name {
    flex: 1;
    font-weight: 500;
  }
}

.rule-content {
  padding: 12px;
}

.rule-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.groups-list {
  padding: 0 12px;
}

.group-item {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 12px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.group-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
}

.group-components {
  .el-select {
    width: 100%;
  }
}

.state-panel {
  padding: 12px;
}

.state-section {
  margin-bottom: 24px;
  
  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    color: #606266;
  }
}

.active-rules {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filters-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.no-data {
  color: #909399;
  font-size: 13px;
}

.state-actions {
  display: flex;
  gap: 8px;
  margin-top: 24px;
}

.history-panel {
  padding: 12px;
}

.history-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
