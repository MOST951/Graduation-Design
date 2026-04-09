/**
 * 图表联动 Composable
 * 用于在图表组件中集成联动功能
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useLinkageStore } from '@/store/bindage';
import type { TriggerType, LinkageEvent } from '@/api/bindage';

export interface UseLinkageOptions {
  componentId: string;
  onFilter?: (data: any) => void;
  onHighlight?: (data: any[]) => void;
  onDrillDown?: (data: any) => void;
  onSyncZoom?: (range: { start: any; end: any }) => void;
  onSyncSelection?: (data: any[]) => void;
}

export function useLinkage(options: UseLinkageOptions) {
  const linkageStore = useLinkageStore();
  
  const {
    componentId,
    onFilter,
    onHighlight,
    onDrillDown,
    onSyncZoom,
    onSyncSelection,
  } = options;
  
  // 当前组件的联动状态
  const isLinked = computed(() => {
    const linkages = linkageStore.getComponentLinkages(componentId);
    return linkages.asSource.length > 0 || linkages.asTarget.length > 0;
  });
  
  // 当前组件的筛选条件
  const currentFilter = computed(() => {
    const filters = Object.values(linkageStore.activeFilters);
    return filters.find(f => f.affectedComponents?.includes(componentId));
  });
  
  // 当前组件的高亮数据
  const highlightedData = computed(() => {
    return linkageStore.highlightedData[componentId] || [];
  });
  
  // 当前组件的选中数据
  const selectedData = computed(() => {
    return linkageStore.selectedData[componentId] || [];
  });
  
  // 当前缩放范围
  const zoomRange = computed(() => linkageStore.state.zoomRange);
  
  // 下钻路径
  const drillPath = computed(() => linkageStore.drillPath);
  
  // 是否正在预览
  const isPreviewing = computed(() => {
    const rule = linkageStore.previewingRule;
    if (!rule) return false;
    return rule.sourceComponentId === componentId ||
           rule.targetComponentIds.includes(componentId);
  });
  
  /**
   * 触发联动事件
   */
  function trigger(triggerType: TriggerType, data: any) {
    linkageStore.triggerLinkage(componentId, triggerType, data);
  }
  
  /**
   * 触发点击联动
   */
  function triggerClick(data: any) {
    trigger('click', data);
  }
  
  /**
   * 触发悬停联动
   */
  function triggerHover(data: any) {
    trigger('hover', data);
  }
  
  /**
   * 触发选择联动
   */
  function triggerSelect(data: any) {
    trigger('select', data);
  }
  
  /**
   * 触发框选联动
   */
  function triggerBrush(data: any) {
    trigger('brush', data);
  }
  
  /**
   * 触发缩放联动
   */
  function triggerZoom(range: { start: any; end: any }) {
    trigger('zoom', range);
  }
  
  /**
   * 清除当前组件的高亮
   */
  function clearHighlight() {
    linkageStore.clearHighlight(componentId);
  }
  
  /**
   * 清除当前组件的选择
   */
  function clearSelection() {
    linkageStore.clearSelection(componentId);
  }
  
  /**
   * 处理联动事件
   */
  function handleLinkageEvent(event: LinkageEvent) {
    // 根据规则类型调用相应的回调
    const rule = linkageStore.rules.find(r => r.id === event.ruleId);
    if (!rule) return;
    
    switch (rule.linkageType) {
      case 'filter':
        onFilter?.(event.data);
        break;
      case 'highlight':
        onHighlight?.(Array.isArray(event.data) ? event.data : [event.data]);
        break;
      case 'drill-down':
        onDrillDown?.(event.data);
        break;
      case 'sync-zoom':
        onSyncZoom?.(event.data);
        break;
      case 'sync-selection':
        onSyncSelection?.(Array.isArray(event.data) ? event.data : [event.data]);
        break;
    }
  }
  
  // 监听联动事件
  onMounted(() => {
    linkageStore.addEventListener(componentId, handleLinkageEvent);
  });
  
  onUnmounted(() => {
    linkageStore.removeEventListener(componentId, handleLinkageEvent);
  });
  
  // 监听筛选变化
  watch(currentFilter, (filter) => {
    if (filter && onFilter) {
      onFilter(filter.value);
    }
  });
  
  // 监听高亮变化
  watch(highlightedData, (data) => {
    if (data.length > 0 && onHighlight) {
      onHighlight(data);
    }
  });
  
  // 监听缩放范围变化
  watch(zoomRange, (range) => {
    if (range && onSyncZoom) {
      onSyncZoom(range);
    }
  });
  
  return {
    // 状态
    isLinked,
    currentFilter,
    highlightedData,
    selectedData,
    zoomRange,
    drillPath,
    isPreviewing,
    
    // 触发方法
    trigger,
    triggerClick,
    triggerHover,
    triggerSelect,
    triggerBrush,
    triggerZoom,
    
    // 清除方法
    clearHighlight,
    clearSelection,
  };
}

/**
 * 创建 ECharts 联动事件处理器
 */
export function createEChartsLinkageHandlers(
  componentId: string,
  chart: any
) {
  const linkageStore = useLinkageStore();
  
  // 点击事件
  chart.on('click', (params: any) => {
    linkageStore.triggerLinkage(componentId, 'click', {
      name: params.name,
      value: params.value,
      dataIndex: params.dataIndex,
      seriesName: params.seriesName,
      data: params.data,
    });
  });
  
  // 悬停事件
  let hoverTimeout: number | null = null;
  chart.on('mouseover', (params: any) => {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    hoverTimeout = window.setTimeout(() => {
      linkageStore.triggerLinkage(componentId, 'hover', {
        name: params.name,
        value: params.value,
        dataIndex: params.dataIndex,
        seriesName: params.seriesName,
        data: params.data,
      });
    }, 100);
  });
  
  chart.on('mouseout', () => {
    if (hoverTimeout) clearTimeout(hoverTimeout);
    linkageStore.clearHighlight();
  });
  
  // 框选事件
  chart.on('brushSelected', (params: any) => {
    const selected = params.batch?.[0]?.selected || [];
    const selectedData = selected.flatMap((s: any) => s.dataIndex.map((i: number) => s.data?.[i]));
    
    if (selectedData.length > 0) {
      linkageStore.triggerLinkage(componentId, 'brush', selectedData);
    }
  });
  
  // 缩放事件
  chart.on('datazoom', (params: any) => {
    linkageStore.triggerLinkage(componentId, 'zoom', {
      start: params.start,
      end: params.end,
      startValue: params.startValue,
      endValue: params.endValue,
    });
  });
  
  // 监听联动事件并更新图表
  const handleLinkageEvent = (event: LinkageEvent) => {
    const rule = linkageStore.rules.find(r => r.id === event.ruleId);
    if (!rule) return;
    
    switch (rule.linkageType) {
      case 'highlight':
        // 高亮对应数据点
        chart.dispatchAction({
          type: 'highlight',
          name: event.data.name,
        });
        break;
        
      case 'sync-zoom':
        // 同步缩放
        chart.dispatchAction({
          type: 'dataZoom',
          start: event.data.start,
          end: event.data.end,
        });
        break;
        
      case 'sync-selection':
        // 同步选择
        chart.dispatchAction({
          type: 'select',
          name: event.data.map((d: any) => d.name),
        });
        break;
    }
  };
  
  linkageStore.addEventListener(componentId, handleLinkageEvent);
  
  // 返回清理函数
  return () => {
    linkageStore.removeEventListener(componentId, handleLinkageEvent);
    chart.off('click');
    chart.off('mouseover');
    chart.off('mouseout');
    chart.off('brushSelected');
    chart.off('datazoom');
  };
}

/**
 * 应用筛选到数据
 */
export function applyFilterToData<T>(
  data: T[],
  filter: any,
  fieldMapping?: Record<string, keyof T>
): T[] {
  if (!filter) return data;
  
  const filterValue = filter.value;
  const filterField = filter.field;
  
  return data.filter(item => {
    const field = fieldMapping?.[filterField] || filterField;
    const value = item[field as keyof T];
    
    if (typeof filterValue === 'string') {
      return String(value).includes(filterValue);
    } else if (typeof filterValue === 'object' && filterValue.name) {
      return value === filterValue.name;
    } else {
      return value === filterValue;
    }
  });
}

/**
 * 获取高亮样式
 */
export function getHighlightStyle(
  dataItem: any,
  highlightedData: any[],
  normalStyle: any,
  highlightStyle: any
): any {
  const isHighlighted = highlightedData.some(h => 
    h.name === dataItem.name || h.value === dataItem.value
  );
  
  return isHighlighted ? { ...normalStyle, ...highlightStyle } : normalStyle;
}
