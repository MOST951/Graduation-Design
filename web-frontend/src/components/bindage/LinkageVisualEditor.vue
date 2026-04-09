<template>
  <div class="linkage-visual-editor">
    <div class="editor-header">
      <h3>可视化联动配置</h3>
      <div class="header-actions">
        <el-button size="small" @click="autoLayout">自动布局</el-button>
        <el-button size="small" @click="clearConnections">清除连线</el-button>
      </div>
    </div>
    
    <div ref="editorRef" class="editor-content">
      <!-- 组件节点 -->
      <div
        v-for="node in nodes"
        :key="node.id"
        class="component-node"
        :class="{ 
          selected: selectedNode === node.id,
          'is-source': isSourceNode(node.id),
          'is-target': isTargetNode(node.id),
        }"
        :style="{ left: node.x + 'px', top: node.y + 'px' }"
        @mousedown="handleNodeMouseDown($event, node)"
        @click="handleNodeClick(node)"
      >
        <div class="node-header" :style="{ backgroundColor: getNodeColor(node) }">
          <el-icon :size="16">
            <component :is="getNodeIcon(node.type)" />
          </el-icon>
          <span>{{ node.name }}</span>
        </div>
        <div class="node-body">
          <div class="node-type">{{ getTypeName(node.type) }}</div>
          <div class="node-linkages">
            <el-tag
              v-for="linkage in getNodeLinkages(node.id)"
              :key="linkage.id"
              size="small"
              :type="linkage.direction === 'source' ? 'primary' : 'success'"
            >
              {{ linkage.direction === 'source' ? '→' : '←' }} {{ linkage.count }}
            </el-tag>
          </div>
        </div>
        
        <!-- 连接点 -->
        <div
          class="connection-point output"
          @mousedown.stop="startConnection($event, node, 'output')"
        ></div>
        <div
          class="connection-point input"
          @mousedown.stop="startConnection($event, node, 'input')"
        ></div>
      </div>
      
      <!-- 连线 SVG -->
      <svg class="connections-svg" :width="svgWidth" :height="svgHeight">
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#409EFF" />
          </marker>
          <marker
            id="arrowhead-highlight"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#67C23A" />
          </marker>
        </defs>
        
        <!-- 已有连线 -->
        <g v-for="connection in connections" :key="connection.id">
          <path
            :d="getConnectionPath(connection)"
            :class="['connection-line', { highlighted: highlightedConnection === connection.id }]"
            :stroke="highlightedConnection === connection.id ? '#67C23A' : '#409EFF'"
            stroke-width="2"
            fill="none"
            :marker-end="highlightedConnection === connection.id ? 'url(#arrowhead-highlight)' : 'url(#arrowhead)'"
            @click="handleConnectionClick(connection)"
            @mouseenter="highlightedConnection = connection.id"
            @mouseleave="highlightedConnection = null"
          />
          <!-- 联动类型标签 -->
          <foreignObject
            :x="getConnectionLabelPosition(connection).x - 30"
            :y="getConnectionLabelPosition(connection).y - 10"
            width="60"
            height="20"
          >
            <div class="connection-label">
              {{ getLinkageTypeName(connection.linkageType) }}
            </div>
          </foreignObject>
        </g>
        
        <!-- 正在绘制的连线 -->
        <path
          v-if="drawingConnection"
          :d="getDrawingPath()"
          class="connection-line drawing"
          stroke="#909399"
          stroke-width="2"
          stroke-dasharray="5,5"
          fill="none"
        />
      </svg>
    </div>
    
    <!-- 连线配置弹窗 -->
    <el-dialog
      v-model="showConnectionDialog"
      title="配置联动"
      width="400px"
      @close="cancelConnection"
    >
      <el-form label-position="top" size="small">
        <el-form-item label="联动类型">
          <el-select v-model="newConnection.linkageType">
            <el-option label="数据筛选" value="filter" />
            <el-option label="高亮显示" value="highlight" />
            <el-option label="下钻分析" value="drill-down" />
            <el-option label="同步缩放" value="sync-zoom" />
            <el-option label="同步选择" value="sync-selection" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发条件">
          <el-select v-model="newConnection.triggerType">
            <el-option label="点击" value="click" />
            <el-option label="悬停" value="hover" />
            <el-option label="选择" value="select" />
            <el-option label="框选" value="brush" />
          </el-select>
        </el-form-item>
        <el-form-item label="联动方向">
          <el-radio-group v-model="newConnection.direction">
            <el-radio label="one-way">单向</el-radio>
            <el-radio label="two-way">双向</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelConnection">取消</el-button>
        <el-button type="primary" @click="confirmConnection">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 连线详情弹窗 -->
    <el-dialog
      v-model="showConnectionDetail"
      title="联动详情"
      width="400px"
    >
      <template v-if="selectedConnection">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="源组件">
            {{ getNodeName(selectedConnection.sourceId) }}
          </el-descriptions-item>
          <el-descriptions-item label="目标组件">
            {{ getNodeName(selectedConnection.targetId) }}
          </el-descriptions-item>
          <el-descriptions-item label="联动类型">
            {{ getLinkageTypeName(selectedConnection.linkageType) }}
          </el-descriptions-item>
          <el-descriptions-item label="触发条件">
            {{ getTriggerTypeName(selectedConnection.triggerType) }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <el-button type="danger" @click="deleteSelectedConnection">删除联动</el-button>
        <el-button @click="showConnectionDetail = false">关闭</el-button>
      </template>
    </el-dialog>
    
    <!-- 图例 -->
    <div class="legend">
      <div class="legend-item">
        <div class="legend-color source"></div>
        <span>源组件</span>
      </div>
      <div class="legend-item">
        <div class="legend-color target"></div>
        <span>目标组件</span>
      </div>
      <div class="legend-item">
        <div class="legend-line"></div>
        <span>联动关系</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { useLinkageStore } from '@/store/bindage';
import { useVisualizationStore } from '@/store/visualization';
import {
  type LinkageType,
  type TriggerType,
  type LinkageDirection,
  getLinkageTypeName,
  getTriggerTypeName,
  generateLinkageId,
} from '@/api/bindage';

interface Node {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
}

interface Connection {
  id: string;
  ruleId: string;
  sourceId: string;
  targetId: string;
  linkageType: LinkageType;
  triggerType: TriggerType;
}

const linkageStore = useLinkageStore();
const visualizationStore = useVisualizationStore();

const editorRef = ref<HTMLElement | null>(null);
const svgWidth = ref(800);
const svgHeight = ref(600);

const nodes = ref<Node[]>([]);
const selectedNode = ref<string | null>(null);
const highlightedConnection = ref<string | null>(null);

const drawingConnection = ref(false);
const drawingStart = ref<{ node: Node; type: 'input' | 'output'; x: number; y: number } | null>(null);
const drawingEnd = ref({ x: 0, y: 0 });

const showConnectionDialog = ref(false);
const showConnectionDetail = ref(false);
const selectedConnection = ref<Connection | null>(null);

const newConnection = ref({
  sourceId: '',
  targetId: '',
  linkageType: 'filter' as LinkageType,
  triggerType: 'click' as TriggerType,
  direction: 'one-way' as LinkageDirection,
});

// 从规则生成连线
const connections = computed<Connection[]>(() => {
  const result: Connection[] = [];
  linkageStore.rules.forEach(rule => {
    if (rule.targetType === 'specific') {
      rule.targetComponentIds.forEach(targetId => {
        result.push({
          id: `${rule.id}-${targetId}`,
          ruleId: rule.id,
          sourceId: rule.sourceComponentId,
          targetId,
          linkageType: rule.linkageType,
          triggerType: rule.triggerType,
        });
      });
    }
  });
  return result;
});

// 从画布组件生成节点
watch(() => visualizationStore.canvasComponents, (components) => {
  const existingNodes = new Map(nodes.value.map(n => [n.id, n]));
  
  nodes.value = components.map((comp, index) => {
    const existing = existingNodes.get(comp.id);
    return {
      id: comp.id,
      name: comp.props.title || comp.type,
      type: comp.type,
      x: existing?.x ?? 100 + (index % 4) * 200,
      y: existing?.y ?? 100 + Math.floor(index / 4) * 150,
    };
  });
}, { immediate: true, deep: true });

function getNodeColor(node: Node): string {
  const colors: Record<string, string> = {
    'bar-chart': '#5470c6',
    'line-chart': '#91cc75',
    'pie-chart': '#fac858',
    'scatter-chart': '#ee6666',
    'heatmap-chart': '#73c0de',
    'map-chart': '#3ba272',
    'radar-chart': '#fc8452',
    'gauge-chart': '#9a60b4',
    'metric-card': '#409EFF',
  };
  return colors[node.type] || '#909399';
}

function getNodeIcon(type: string): string {
  const icons: Record<string, string> = {
    'bar-chart': 'Histogram',
    'line-chart': 'TrendCharts',
    'pie-chart': 'PieChart',
    'scatter-chart': 'Coordinate',
    'heatmap-chart': 'Grid',
    'map-chart': 'MapLocation',
    'radar-chart': 'Aim',
    'gauge-chart': 'Odometer',
    'metric-card': 'DataLine',
  };
  return icons[type] || 'Document';
}

function getTypeName(type: string): string {
  const names: Record<string, string> = {
    'bar-chart': '柱状图',
    'line-chart': '折线图',
    'pie-chart': '饼图',
    'scatter-chart': '散点图',
    'heatmap-chart': '热力图',
    'map-chart': '地图',
    'radar-chart': '雷达图',
    'gauge-chart': '仪表盘',
    'metric-card': '指标卡',
  };
  return names[type] || type;
}

function getNodeLinkages(nodeId: string) {
  const asSource = connections.value.filter(c => c.sourceId === nodeId).length;
  const asTarget = connections.value.filter(c => c.targetId === nodeId).length;
  
  const result = [];
  if (asSource > 0) result.push({ id: 'source', direction: 'source', count: asSource });
  if (asTarget > 0) result.push({ id: 'target', direction: 'target', count: asTarget });
  return result;
}

function isSourceNode(nodeId: string): boolean {
  return connections.value.some(c => c.sourceId === nodeId);
}

function isTargetNode(nodeId: string): boolean {
  return connections.value.some(c => c.targetId === nodeId);
}

function getNodeName(nodeId: string): string {
  return nodes.value.find(n => n.id === nodeId)?.name || nodeId;
}

function handleNodeMouseDown(event: MouseEvent, node: Node) {
  const startX = event.clientX;
  const startY = event.clientY;
  const startNodeX = node.x;
  const startNodeY = node.y;
  
  const handleMouseMove = (e: MouseEvent) => {
    node.x = startNodeX + (e.clientX - startX);
    node.y = startNodeY + (e.clientY - startY);
  };
  
  const handleMouseUp = () => {
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
  
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
}

function handleNodeClick(node: Node) {
  selectedNode.value = node.id;
}

function startConnection(event: MouseEvent, node: Node, type: 'input' | 'output') {
  drawingConnection.value = true;
  drawingStart.value = {
    node,
    type,
    x: node.x + (type === 'output' ? 160 : 0),
    y: node.y + 40,
  };
  drawingEnd.value = { x: event.clientX, y: event.clientY };
  
  const handleMouseMove = (e: MouseEvent) => {
    if (!editorRef.value) return;
    const rect = editorRef.value.getBoundingClientRect();
    drawingEnd.value = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  };
  
  const handleMouseUp = (e: MouseEvent) => {
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    
    // 检查是否落在另一个节点上
    const targetNode = findNodeAtPosition(e.clientX, e.clientY);
    if (targetNode && targetNode.id !== node.id) {
      // 打开配置弹窗
      if (type === 'output') {
        newConnection.value.sourceId = node.id;
        newConnection.value.targetId = targetNode.id;
      } else {
        newConnection.value.sourceId = targetNode.id;
        newConnection.value.targetId = node.id;
      }
      showConnectionDialog.value = true;
    }
    
    drawingConnection.value = false;
    drawingStart.value = null;
  };
  
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
}

function findNodeAtPosition(clientX: number, clientY: number): Node | null {
  if (!editorRef.value) return null;
  
  const rect = editorRef.value.getBoundingClientRect();
  const x = clientX - rect.left;
  const y = clientY - rect.top;
  
  return nodes.value.find(node => 
    x >= node.x && x <= node.x + 160 &&
    y >= node.y && y <= node.y + 80
  ) || null;
}

function getConnectionPath(connection: Connection): string {
  const sourceNode = nodes.value.find(n => n.id === connection.sourceId);
  const targetNode = nodes.value.find(n => n.id === connection.targetId);
  
  if (!sourceNode || !targetNode) return '';
  
  const startX = sourceNode.x + 160;
  const startY = sourceNode.y + 40;
  const endX = targetNode.x;
  const endY = targetNode.y + 40;
  
  const midX = (startX + endX) / 2;
  
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
}

function getConnectionLabelPosition(connection: Connection) {
  const sourceNode = nodes.value.find(n => n.id === connection.sourceId);
  const targetNode = nodes.value.find(n => n.id === connection.targetId);
  
  if (!sourceNode || !targetNode) return { x: 0, y: 0 };
  
  return {
    x: (sourceNode.x + 160 + targetNode.x) / 2,
    y: (sourceNode.y + 40 + targetNode.y + 40) / 2,
  };
}

function getDrawingPath(): string {
  if (!drawingStart.value) return '';
  
  const startX = drawingStart.value.x;
  const startY = drawingStart.value.y;
  const endX = drawingEnd.value.x;
  const endY = drawingEnd.value.y;
  
  const midX = (startX + endX) / 2;
  
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
}

function handleConnectionClick(connection: Connection) {
  selectedConnection.value = connection;
  showConnectionDetail.value = true;
}

function confirmConnection() {
  // 创建联动规则
  const rule = linkageStore.addRule(newConnection.value.sourceId);
  linkageStore.updateRule(rule.id, {
    name: `${getNodeName(newConnection.value.sourceId)} → ${getNodeName(newConnection.value.targetId)}`,
    targetType: 'specific',
    targetComponentIds: [newConnection.value.targetId],
    linkageType: newConnection.value.linkageType,
    triggerType: newConnection.value.triggerType,
    direction: newConnection.value.direction,
  });
  
  showConnectionDialog.value = false;
  ElMessage.success('联动规则已创建');
  
  // 重置
  newConnection.value = {
    sourceId: '',
    targetId: '',
    linkageType: 'filter',
    triggerType: 'click',
    direction: 'one-way',
  };
}

function cancelConnection() {
  showConnectionDialog.value = false;
  newConnection.value = {
    sourceId: '',
    targetId: '',
    linkageType: 'filter',
    triggerType: 'click',
    direction: 'one-way',
  };
}

function deleteSelectedConnection() {
  if (selectedConnection.value) {
    linkageStore.removeRule(selectedConnection.value.ruleId);
    showConnectionDetail.value = false;
    selectedConnection.value = null;
    ElMessage.success('联动规则已删除');
  }
}

function autoLayout() {
  const cols = Math.ceil(Math.sqrt(nodes.value.length));
  nodes.value.forEach((node, index) => {
    node.x = 50 + (index % cols) * 200;
    node.y = 50 + Math.floor(index / cols) * 120;
  });
}

function clearConnections() {
  linkageStore.resetConfig();
  ElMessage.success('已清除所有联动');
}

onMounted(() => {
  if (editorRef.value) {
    svgWidth.value = editorRef.value.clientWidth;
    svgHeight.value = editorRef.value.clientHeight;
  }
});
</script>

<style scoped lang="scss">
.linkage-visual-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  
  h3 {
    margin: 0;
    font-size: 16px;
  }
  
  .header-actions {
    display: flex;
    gap: 8px;
  }
}

.editor-content {
  flex: 1;
  position: relative;
  overflow: auto;
  min-height: 400px;
}

.component-node {
  position: absolute;
  width: 160px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  cursor: move;
  transition: box-shadow 0.2s;
  
  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }
  
  &.selected {
    box-shadow: 0 0 0 2px #409EFF;
  }
  
  &.is-source .node-header {
    border-left: 4px solid #409EFF;
  }
  
  &.is-target .node-header {
    border-right: 4px solid #67C23A;
  }
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  color: #fff;
  border-radius: 8px 8px 0 0;
  font-size: 13px;
  font-weight: 500;
}

.node-body {
  padding: 8px 12px;
}

.node-type {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.node-linkages {
  display: flex;
  gap: 4px;
}

.connection-point {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #fff;
  border: 2px solid #409EFF;
  border-radius: 50%;
  cursor: crosshair;
  
  &.output {
    right: -6px;
    top: 50%;
    transform: translateY(-50%);
  }
  
  &.input {
    left: -6px;
    top: 50%;
    transform: translateY(-50%);
  }
  
  &:hover {
    background: #409EFF;
  }
}

.connections-svg {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  
  path {
    pointer-events: stroke;
    cursor: pointer;
    
    &:hover {
      stroke-width: 3;
    }
  }
}

.connection-line {
  transition: stroke 0.2s;
  
  &.highlighted {
    stroke-width: 3;
  }
  
  &.drawing {
    pointer-events: none;
  }
}

.connection-label {
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
}

.legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  display: flex;
  gap: 16px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #606266;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  
  &.source {
    background: #409EFF;
  }
  
  &.target {
    background: #67C23A;
  }
}

.legend-line {
  width: 24px;
  height: 2px;
  background: #409EFF;
}
</style>
