/**
 * 可视化工作台 Store
 */
import { defineStore } from 'pinia';
import { ref, computed, shallowRef } from 'vue';
import {
  getComponentLibrary,
  getLayouts,
  getLayout,
  saveLayout,
  deleteLayout,
  getTemplates,
  saveAsTemplate,
  createFromTemplate,
  exportLayout,
  getDataSources,
  fetchDataSourceData,
  generateShareLink,
  componentLibrary,
  type ComponentDefinition,
  type ComponentType,
  type ComponentCategory,
  type CanvasComponent,
  type LayoutConfig,
  type HistoryItem,
  type DataBinding,
  type ComponentStyles,
} from '@/api/visualization';

// 生成唯一ID
function generateId(): string {
  return `comp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

// 深拷贝
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

export const useVisualizationStore = defineStore('visualization', () => {
  // ==================== State ====================
  
  /** 组件库 */
  const components = ref<ComponentDefinition[]>(componentLibrary);
  
  /** 组件搜索关键词 */
  const searchKeyword = ref('');
  
  /** 当前选中的分类 */
  const selectedCategory = ref<ComponentCategory | 'all'>('all');
  
  /** 当前布局配置 */
  const currentLayout = ref<LayoutConfig>({
    id: '',
    name: '未命名布局',
    canvasWidth: 1920,
    canvasHeight: 1080,
    gridSize: 20,
    snapToGrid: true,
    showGrid: true,
    backgroundColor: '#f5f7fa',
    components: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  });
  
  /** 选中的组件ID列表 */
  const selectedComponentIds = ref<string[]>([]);
  
  /** 剪贴板 */
  const clipboard = ref<CanvasComponent[]>([]);
  
  /** 历史记录 */
  const history = ref<HistoryItem[]>([]);
  
  /** 当前历史索引 */
  const historyIndex = ref(-1);
  
  /** 最大历史记录数 */
  const maxHistorySize = 50;
  
  /** 画布缩放比例 */
  const canvasScale = ref(1);
  
  /** 画布偏移 */
  const canvasOffset = ref({ x: 0, y: 0 });
  
  /** 是否正在拖拽 */
  const isDragging = ref(false);
  
  /** 是否正在调整大小 */
  const isResizing = ref(false);
  
  /** 布局列表 */
  const layouts = ref<LayoutConfig[]>([]);
  
  /** 模板列表 */
  const templates = ref<LayoutConfig[]>([]);
  
  /** 数据源列表 */
  const dataSources = ref<{ id: string; name: string; type: string }[]>([]);
  
  /** 加载状态 */
  const isLoading = ref(false);
  
  /** 是否有未保存的更改 */
  const hasUnsavedChanges = ref(false);
  
  /** 属性面板展开状态 */
  const propertyPanelExpanded = ref(true);
  
  /** 组件库面板展开状态 */
  const componentPanelExpanded = ref(true);
  
  // ==================== Getters ====================
  
  /** 过滤后的组件库 */
  const filteredComponents = computed(() => {
    let result = components.value;
    
    // 按分类过滤
    if (selectedCategory.value !== 'all') {
      result = result.filter(c => c.category === selectedCategory.value);
    }
    
    // 按关键词搜索
    if (searchKeyword.value) {
      const keyword = searchKeyword.value.toLowerCase();
      result = result.filter(c => 
        c.name.toLowerCase().includes(keyword) ||
        c.description.toLowerCase().includes(keyword)
      );
    }
    
    return result;
  });
  
  /** 按分类分组的组件 */
  const groupedComponents = computed(() => {
    const groups: Record<ComponentCategory, ComponentDefinition[]> = {
      chart: [],
      text: [],
      control: [],
      layout: [],
    };
    
    filteredComponents.value.forEach(c => {
      groups[c.category].push(c);
    });
    
    return groups;
  });
  
  /** 画布上的组件 */
  const canvasComponents = computed(() => currentLayout.value.components);
  
  /** 选中的组件 */
  const selectedComponents = computed(() => 
    canvasComponents.value.filter(c => selectedComponentIds.value.includes(c.id))
  );
  
  /** 当前选中的单个组件 */
  const activeComponent = computed(() => 
    selectedComponentIds.value.length === 1 
      ? canvasComponents.value.find(c => c.id === selectedComponentIds.value[0]) 
      : null
  );
  
  /** 是否可以撤销 */
  const canUndo = computed(() => historyIndex.value > 0);
  
  /** 是否可以重做 */
  const canRedo = computed(() => historyIndex.value < history.value.length - 1);
  
  /** 组件层级列表（按zIndex排序） */
  const layerList = computed(() => 
    [...canvasComponents.value].sort((a, b) => b.zIndex - a.zIndex)
  );
  
  // ==================== Actions ====================
  
  /**
   * 初始化
   */
  async function initialize() {
    isLoading.value = true;
    try {
      const [layoutList, templateList, sourceList] = await Promise.all([
        getLayouts(),
        getTemplates(),
        getDataSources(),
      ]);
      layouts.value = layoutList;
      templates.value = templateList;
      dataSources.value = sourceList;
      
      // 初始化历史记录
      saveToHistory('初始化');
    } catch (error) {
      console.error('初始化失败:', error);
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 保存到历史记录
   */
  function saveToHistory(description: string) {
    // 删除当前索引之后的历史
    if (historyIndex.value < history.value.length - 1) {
      history.value = history.value.slice(0, historyIndex.value + 1);
    }
    
    // 添加新历史
    const item: HistoryItem = {
      id: generateId(),
      action: 'batch',
      timestamp: Date.now(),
      components: deepClone(currentLayout.value.components),
      description,
    };
    
    history.value.push(item);
    
    // 限制历史记录数量
    if (history.value.length > maxHistorySize) {
      history.value.shift();
    } else {
      historyIndex.value++;
    }
    
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 撤销
   */
  function undo() {
    if (!canUndo.value) return;
    
    historyIndex.value--;
    currentLayout.value.components = deepClone(history.value[historyIndex.value].components);
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 重做
   */
  function redo() {
    if (!canRedo.value) return;
    
    historyIndex.value++;
    currentLayout.value.components = deepClone(history.value[historyIndex.value].components);
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 添加组件到画布
   */
  function addComponent(type: ComponentType, position?: { x: number; y: number }) {
    const definition = components.value.find(c => c.type === type);
    if (!definition) return null;
    
    const maxZIndex = canvasComponents.value.reduce((max, c) => Math.max(max, c.zIndex), 0);
    
    const component: CanvasComponent = {
      id: generateId(),
      type,
      x: position?.x ?? 100,
      y: position?.y ?? 100,
      width: definition.defaultWidth,
      height: definition.defaultHeight,
      zIndex: maxZIndex + 1,
      locked: false,
      visible: true,
      props: deepClone(definition.defaultProps),
      styles: {
        backgroundColor: 'transparent',
        borderColor: '#e4e7ed',
        borderWidth: 0,
        borderRadius: 4,
        padding: 12,
        opacity: 1,
      },
    };
    
    // 对齐到网格
    if (currentLayout.value.snapToGrid) {
      const gridSize = currentLayout.value.gridSize;
      component.x = Math.round(component.x / gridSize) * gridSize;
      component.y = Math.round(component.y / gridSize) * gridSize;
    }
    
    currentLayout.value.components.push(component);
    selectedComponentIds.value = [component.id];
    
    saveToHistory(`添加${definition.name}`);
    
    return component;
  }
  
  /**
   * 删除组件
   */
  function removeComponents(ids: string[]) {
    const toRemove = new Set(ids);
    currentLayout.value.components = currentLayout.value.components.filter(
      c => !toRemove.has(c.id)
    );
    selectedComponentIds.value = selectedComponentIds.value.filter(id => !toRemove.has(id));
    
    saveToHistory(`删除${ids.length}个组件`);
  }
  
  /**
   * 删除选中的组件
   */
  function removeSelectedComponents() {
    if (selectedComponentIds.value.length === 0) return;
    removeComponents(selectedComponentIds.value);
  }
  
  /**
   * 更新组件属性
   */
  function updateComponent(id: string, updates: Partial<CanvasComponent>) {
    const index = currentLayout.value.components.findIndex(c => c.id === id);
    if (index === -1) return;
    
    const component = currentLayout.value.components[index];
    currentLayout.value.components[index] = { ...component, ...updates };
    
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 更新组件属性（带历史记录）
   */
  function updateComponentWithHistory(id: string, updates: Partial<CanvasComponent>, description: string) {
    updateComponent(id, updates);
    saveToHistory(description);
  }
  
  /**
   * 更新组件props
   */
  function updateComponentProps(id: string, props: Record<string, any>) {
    const component = currentLayout.value.components.find(c => c.id === id);
    if (!component) return;
    
    component.props = { ...component.props, ...props };
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 更新组件样式
   */
  function updateComponentStyles(id: string, styles: Partial<ComponentStyles>) {
    const component = currentLayout.value.components.find(c => c.id === id);
    if (!component) return;
    
    component.styles = { ...component.styles, ...styles };
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 更新组件数据绑定
   */
  function updateComponentDataBinding(id: string, binding: DataBinding | undefined) {
    const component = currentLayout.value.components.find(c => c.id === id);
    if (!component) return;
    
    component.dataBinding = binding;
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 移动组件
   */
  function moveComponent(id: string, x: number, y: number) {
    const component = currentLayout.value.components.find(c => c.id === id);
    if (!component || component.locked) return;
    
    // 对齐到网格
    if (currentLayout.value.snapToGrid) {
      const gridSize = currentLayout.value.gridSize;
      x = Math.round(x / gridSize) * gridSize;
      y = Math.round(y / gridSize) * gridSize;
    }
    
    component.x = Math.max(0, x);
    component.y = Math.max(0, y);
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 调整组件大小
   */
  function resizeComponent(id: string, width: number, height: number) {
    const component = currentLayout.value.components.find(c => c.id === id);
    if (!component || component.locked) return;
    
    const definition = components.value.find(c => c.type === component.type);
    if (!definition) return;
    
    // 对齐到网格
    if (currentLayout.value.snapToGrid) {
      const gridSize = currentLayout.value.gridSize;
      width = Math.round(width / gridSize) * gridSize;
      height = Math.round(height / gridSize) * gridSize;
    }
    
    component.width = Math.max(definition.minWidth, width);
    component.height = Math.max(definition.minHeight, height);
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 选中组件
   */
  function selectComponent(id: string, append = false) {
    if (append) {
      if (selectedComponentIds.value.includes(id)) {
        selectedComponentIds.value = selectedComponentIds.value.filter(i => i !== id);
      } else {
        selectedComponentIds.value.push(id);
      }
    } else {
      selectedComponentIds.value = [id];
    }
  }
  
  /**
   * 全选组件
   */
  function selectAllComponents() {
    selectedComponentIds.value = canvasComponents.value.map(c => c.id);
  }
  
  /**
   * 取消选中
   */
  function clearSelection() {
    selectedComponentIds.value = [];
  }
  
  /**
   * 复制选中的组件
   */
  function copySelectedComponents() {
    clipboard.value = deepClone(selectedComponents.value);
  }
  
  /**
   * 剪切选中的组件
   */
  function cutSelectedComponents() {
    copySelectedComponents();
    removeSelectedComponents();
  }
  
  /**
   * 粘贴组件
   */
  function pasteComponents() {
    if (clipboard.value.length === 0) return;
    
    const offset = 20;
    const newComponents: CanvasComponent[] = clipboard.value.map(c => ({
      ...deepClone(c),
      id: generateId(),
      x: c.x + offset,
      y: c.y + offset,
    }));
    
    currentLayout.value.components.push(...newComponents);
    selectedComponentIds.value = newComponents.map(c => c.id);
    
    // 更新剪贴板位置
    clipboard.value = newComponents.map(c => ({ ...c }));
    
    saveToHistory(`粘贴${newComponents.length}个组件`);
  }
  
  /**
   * 复制组件
   */
  function duplicateComponents(ids: string[]) {
    const toDuplicate = canvasComponents.value.filter(c => ids.includes(c.id));
    const offset = 20;
    
    const newComponents: CanvasComponent[] = toDuplicate.map(c => ({
      ...deepClone(c),
      id: generateId(),
      x: c.x + offset,
      y: c.y + offset,
    }));
    
    currentLayout.value.components.push(...newComponents);
    selectedComponentIds.value = newComponents.map(c => c.id);
    
    saveToHistory(`复制${newComponents.length}个组件`);
  }
  
  /**
   * 锁定/解锁组件
   */
  function toggleLock(id: string) {
    const component = currentLayout.value.components.find(c => c.id === id);
    if (!component) return;
    
    component.locked = !component.locked;
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 显示/隐藏组件
   */
  function toggleVisibility(id: string) {
    const component = currentLayout.value.components.find(c => c.id === id);
    if (!component) return;
    
    component.visible = !component.visible;
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 调整层级
   */
  function changeZIndex(id: string, action: 'top' | 'bottom' | 'up' | 'down') {
    const component = currentLayout.value.components.find(c => c.id === id);
    if (!component) return;
    
    const zIndexes = canvasComponents.value.map(c => c.zIndex).sort((a, b) => a - b);
    const currentIndex = zIndexes.indexOf(component.zIndex);
    
    switch (action) {
      case 'top':
        component.zIndex = Math.max(...zIndexes) + 1;
        break;
      case 'bottom':
        component.zIndex = Math.min(...zIndexes) - 1;
        break;
      case 'up':
        if (currentIndex < zIndexes.length - 1) {
          const targetComponent = canvasComponents.value.find(c => c.zIndex === zIndexes[currentIndex + 1]);
          if (targetComponent) {
            const temp = component.zIndex;
            component.zIndex = targetComponent.zIndex;
            targetComponent.zIndex = temp;
          }
        }
        break;
      case 'down':
        if (currentIndex > 0) {
          const targetComponent = canvasComponents.value.find(c => c.zIndex === zIndexes[currentIndex - 1]);
          if (targetComponent) {
            const temp = component.zIndex;
            component.zIndex = targetComponent.zIndex;
            targetComponent.zIndex = temp;
          }
        }
        break;
    }
    
    saveToHistory('调整层级');
  }
  
  /**
   * 对齐组件
   */
  function alignComponents(alignment: 'left' | 'center' | 'right' | 'top' | 'middle' | 'bottom') {
    if (selectedComponents.value.length < 2) return;
    
    const bounds = selectedComponents.value.reduce(
      (acc, c) => ({
        minX: Math.min(acc.minX, c.x),
        maxX: Math.max(acc.maxX, c.x + c.width),
        minY: Math.min(acc.minY, c.y),
        maxY: Math.max(acc.maxY, c.y + c.height),
      }),
      { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity }
    );
    
    selectedComponents.value.forEach(c => {
      if (c.locked) return;
      
      switch (alignment) {
        case 'left':
          c.x = bounds.minX;
          break;
        case 'center':
          c.x = bounds.minX + (bounds.maxX - bounds.minX - c.width) / 2;
          break;
        case 'right':
          c.x = bounds.maxX - c.width;
          break;
        case 'top':
          c.y = bounds.minY;
          break;
        case 'middle':
          c.y = bounds.minY + (bounds.maxY - bounds.minY - c.height) / 2;
          break;
        case 'bottom':
          c.y = bounds.maxY - c.height;
          break;
      }
    });
    
    saveToHistory(`对齐组件`);
  }
  
  /**
   * 分布组件
   */
  function distributeComponents(direction: 'horizontal' | 'vertical') {
    if (selectedComponents.value.length < 3) return;
    
    const sorted = [...selectedComponents.value].sort((a, b) => 
      direction === 'horizontal' ? a.x - b.x : a.y - b.y
    );
    
    const first = sorted[0];
    const last = sorted[sorted.length - 1];
    
    if (direction === 'horizontal') {
      const totalWidth = sorted.reduce((sum, c) => sum + c.width, 0);
      const space = (last.x + last.width - first.x - totalWidth) / (sorted.length - 1);
      
      let currentX = first.x + first.width + space;
      for (let i = 1; i < sorted.length - 1; i++) {
        if (!sorted[i].locked) {
          sorted[i].x = currentX;
        }
        currentX += sorted[i].width + space;
      }
    } else {
      const totalHeight = sorted.reduce((sum, c) => sum + c.height, 0);
      const space = (last.y + last.height - first.y - totalHeight) / (sorted.length - 1);
      
      let currentY = first.y + first.height + space;
      for (let i = 1; i < sorted.length - 1; i++) {
        if (!sorted[i].locked) {
          sorted[i].y = currentY;
        }
        currentY += sorted[i].height + space;
      }
    }
    
    saveToHistory(`分布组件`);
  }
  
  /**
   * 设置画布缩放
   */
  function setCanvasScale(scale: number) {
    canvasScale.value = Math.max(0.1, Math.min(3, scale));
  }
  
  /**
   * 重置画布视图
   */
  function resetCanvasView() {
    canvasScale.value = 1;
    canvasOffset.value = { x: 0, y: 0 };
  }
  
  /**
   * 适应画布
   */
  function fitToCanvas(containerWidth: number, containerHeight: number) {
    const scaleX = containerWidth / currentLayout.value.canvasWidth;
    const scaleY = containerHeight / currentLayout.value.canvasHeight;
    canvasScale.value = Math.min(scaleX, scaleY, 1) * 0.9;
    canvasOffset.value = { x: 0, y: 0 };
  }
  
  /**
   * 更新布局设置
   */
  function updateLayoutSettings(settings: Partial<LayoutConfig>) {
    Object.assign(currentLayout.value, settings);
    hasUnsavedChanges.value = true;
  }
  
  /**
   * 清空画布
   */
  function clearCanvas() {
    currentLayout.value.components = [];
    selectedComponentIds.value = [];
    saveToHistory('清空画布');
  }
  
  /**
   * 保存当前布局
   */
  async function saveCurrentLayout() {
    isLoading.value = true;
    try {
      const saved = await saveLayout(currentLayout.value);
      currentLayout.value = saved;
      hasUnsavedChanges.value = false;
      
      // 更新布局列表
      const index = layouts.value.findIndex(l => l.id === saved.id);
      if (index !== -1) {
        layouts.value[index] = saved;
      } else {
        layouts.value.push(saved);
      }
      
      return saved;
    } catch (error) {
      console.error('保存布局失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 加载布局
   */
  async function loadLayout(id: string) {
    isLoading.value = true;
    try {
      const layout = await getLayout(id);
      if (layout) {
        currentLayout.value = layout;
        selectedComponentIds.value = [];
        history.value = [];
        historyIndex.value = -1;
        saveToHistory('加载布局');
        hasUnsavedChanges.value = false;
      }
      return layout;
    } catch (error) {
      console.error('加载布局失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 新建布局
   */
  function newLayout() {
    currentLayout.value = {
      id: '',
      name: '未命名布局',
      canvasWidth: 1920,
      canvasHeight: 1080,
      gridSize: 20,
      snapToGrid: true,
      showGrid: true,
      backgroundColor: '#f5f7fa',
      components: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    selectedComponentIds.value = [];
    history.value = [];
    historyIndex.value = -1;
    saveToHistory('新建布局');
    hasUnsavedChanges.value = false;
  }
  
  /**
   * 删除布局
   */
  async function removeLayout(id: string) {
    isLoading.value = true;
    try {
      await deleteLayout(id);
      layouts.value = layouts.value.filter(l => l.id !== id);
      
      if (currentLayout.value.id === id) {
        newLayout();
      }
    } catch (error) {
      console.error('删除布局失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 另存为模板
   */
  async function saveCurrentAsTemplate(name: string, description?: string) {
    isLoading.value = true;
    try {
      const template = await saveAsTemplate(currentLayout.value, name, description);
      templates.value.push(template);
      return template;
    } catch (error) {
      console.error('保存模板失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 从模板创建
   */
  async function createLayoutFromTemplate(templateId: string) {
    isLoading.value = true;
    try {
      const layout = await createFromTemplate(templateId);
      currentLayout.value = layout;
      selectedComponentIds.value = [];
      history.value = [];
      historyIndex.value = -1;
      saveToHistory('从模板创建');
      hasUnsavedChanges.value = true;
      return layout;
    } catch (error) {
      console.error('从模板创建失败:', error);
      throw error;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 导出布局
   */
  async function exportCurrentLayout() {
    try {
      const blob = await exportLayout(currentLayout.value);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentLayout.value.name || 'layout'}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('导出失败:', error);
      throw error;
    }
  }
  
  /**
   * 导入布局
   */
  function importLayout(file: File): Promise<void> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const layout = JSON.parse(e.target?.result as string) as LayoutConfig;
          layout.id = ''; // 清空ID，保存时会生成新ID
          layout.createdAt = new Date().toISOString();
          layout.updatedAt = new Date().toISOString();
          currentLayout.value = layout;
          selectedComponentIds.value = [];
          history.value = [];
          historyIndex.value = -1;
          saveToHistory('导入布局');
          hasUnsavedChanges.value = true;
          resolve();
        } catch (error) {
          reject(new Error('无效的布局文件'));
        }
      };
      reader.onerror = () => reject(new Error('读取文件失败'));
      reader.readAsText(file);
    });
  }
  
  /**
   * 生成分享链接
   */
  async function shareLayout() {
    if (!currentLayout.value.id) {
      await saveCurrentLayout();
    }
    return generateShareLink(currentLayout.value.id);
  }
  
  /**
   * 获取数据源数据
   */
  async function fetchData(sourceId: string, params?: Record<string, any>) {
    return fetchDataSourceData(sourceId, params);
  }
  
  /**
   * 刷新布局列表
   */
  async function refreshLayouts() {
    isLoading.value = true;
    try {
      layouts.value = await getLayouts();
    } catch (error) {
      console.error('刷新布局列表失败:', error);
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * 重置 Store
   */
  function $reset() {
    searchKeyword.value = '';
    selectedCategory.value = 'all';
    newLayout();
    clipboard.value = [];
    canvasScale.value = 1;
    canvasOffset.value = { x: 0, y: 0 };
    isDragging.value = false;
    isResizing.value = false;
    isLoading.value = false;
    propertyPanelExpanded.value = true;
    componentPanelExpanded.value = true;
  }

  return {
    // State
    components,
    searchKeyword,
    selectedCategory,
    currentLayout,
    selectedComponentIds,
    clipboard,
    history,
    historyIndex,
    canvasScale,
    canvasOffset,
    isDragging,
    isResizing,
    layouts,
    templates,
    dataSources,
    isLoading,
    hasUnsavedChanges,
    propertyPanelExpanded,
    componentPanelExpanded,
    
    // Getters
    filteredComponents,
    groupedComponents,
    canvasComponents,
    selectedComponents,
    activeComponent,
    canUndo,
    canRedo,
    layerList,
    
    // Actions
    initialize,
    saveToHistory,
    undo,
    redo,
    addComponent,
    removeComponents,
    removeSelectedComponents,
    updateComponent,
    updateComponentWithHistory,
    updateComponentProps,
    updateComponentStyles,
    updateComponentDataBinding,
    moveComponent,
    resizeComponent,
    selectComponent,
    selectAllComponents,
    clearSelection,
    copySelectedComponents,
    cutSelectedComponents,
    pasteComponents,
    duplicateComponents,
    toggleLock,
    toggleVisibility,
    changeZIndex,
    alignComponents,
    distributeComponents,
    setCanvasScale,
    resetCanvasView,
    fitToCanvas,
    updateLayoutSettings,
    clearCanvas,
    saveCurrentLayout,
    loadLayout,
    newLayout,
    removeLayout,
    saveCurrentAsTemplate,
    createLayoutFromTemplate,
    exportCurrentLayout,
    importLayout,
    shareLayout,
    fetchData,
    refreshLayouts,
    $reset,
  };
});
