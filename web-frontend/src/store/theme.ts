/**
 * 主题管理 Store
 */
import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';
import {
  type ThemeConfig,
  type ThemeApplication,
  type ThemeScope,
  builtInThemes,
  lightTheme,
  createDefaultTheme,
  applyThemeToCSS,
  applyThemeToECharts,
  exportTheme,
  importTheme,
  generateThemeThumbnail,
  generateThemeId,
} from '@/api/theme';

// 深拷贝
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

// 本地存储键
const STORAGE_KEY_THEMES = 'visualization_custom_themes';
const STORAGE_KEY_CURRENT = 'visualization_current_theme';
const STORAGE_KEY_APPLICATIONS = 'visualization_theme_applications';

export const useThemeStore = defineStore('theme', () => {
  // ==================== State ====================
  
  /** 内置主题 */
  const builtIn = ref<ThemeConfig[]>(builtInThemes);
  
  /** 自定义主题 */
  const custom = ref<ThemeConfig[]>([]);
  
  /** 当前全局主题 */
  const currentTheme = ref<ThemeConfig>(lightTheme);
  
  /** 主题应用配置 */
  const applications = ref<ThemeApplication[]>([]);
  
  /** 正在编辑的主题 */
  const editingTheme = ref<ThemeConfig | null>(null);
  
  /** 是否正在加载 */
  const isLoading = ref(false);
  
  // ==================== Getters ====================
  
  /** 所有主题 */
  const allThemes = computed(() => [...builtIn.value, ...custom.value]);
  
  /** 明亮主题列表 */
  const lightThemes = computed(() => allThemes.value.filter(t => !t.isDark));
  
  /** 暗黑主题列表 */
  const darkThemes = computed(() => allThemes.value.filter(t => t.isDark));
  
  /** 当前主题是否为暗黑模式 */
  const isDarkMode = computed(() => currentTheme.value.isDark);
  
  /** ECharts主题配置 */
  const echartsTheme = computed(() => applyThemeToECharts(currentTheme.value));
  
  /** 组件特定主题映射 */
  const componentThemes = computed(() => {
    const map = new Map<string, ThemeConfig>();
    applications.value.forEach(app => {
      if (app.scope === 'component' && app.componentIds) {
        const theme = allThemes.value.find(t => t.id === app.themeId);
        if (theme) {
          app.componentIds.forEach(id => {
            map.set(id, theme);
          });
        }
      }
    });
    return map;
  });
  
  // ==================== Actions ====================
  
  /**
   * 初始化
   */
  function initialize() {
    // 加载自定义主题
    loadCustomThemes();
    
    // 加载当前主题
    loadCurrentTheme();
    
    // 加载主题应用配置
    loadApplications();
    
    // 应用主题
    applyTheme(currentTheme.value);
  }
  
  /**
   * 从本地存储加载自定义主题
   */
  function loadCustomThemes() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_THEMES);
      if (stored) {
        custom.value = JSON.parse(stored);
      }
    } catch (error) {
      console.error('加载自定义主题失败:', error);
    }
  }
  
  /**
   * 保存自定义主题到本地存储
   */
  function saveCustomThemes() {
    try {
      localStorage.setItem(STORAGE_KEY_THEMES, JSON.stringify(custom.value));
    } catch (error) {
      console.error('保存自定义主题失败:', error);
    }
  }
  
  /**
   * 从本地存储加载当前主题
   */
  function loadCurrentTheme() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_CURRENT);
      if (stored) {
        const themeId = JSON.parse(stored);
        const theme = allThemes.value.find(t => t.id === themeId);
        if (theme) {
          currentTheme.value = theme;
        }
      }
    } catch (error) {
      console.error('加载当前主题失败:', error);
    }
  }
  
  /**
   * 保存当前主题到本地存储
   */
  function saveCurrentTheme() {
    try {
      localStorage.setItem(STORAGE_KEY_CURRENT, JSON.stringify(currentTheme.value.id));
    } catch (error) {
      console.error('保存当前主题失败:', error);
    }
  }
  
  /**
   * 从本地存储加载主题应用配置
   */
  function loadApplications() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_APPLICATIONS);
      if (stored) {
        applications.value = JSON.parse(stored);
      }
    } catch (error) {
      console.error('加载主题应用配置失败:', error);
    }
  }
  
  /**
   * 保存主题应用配置到本地存储
   */
  function saveApplications() {
    try {
      localStorage.setItem(STORAGE_KEY_APPLICATIONS, JSON.stringify(applications.value));
    } catch (error) {
      console.error('保存主题应用配置失败:', error);
    }
  }
  
  /**
   * 应用主题
   */
  function applyTheme(theme: ThemeConfig) {
    currentTheme.value = theme;
    applyThemeToCSS(theme);
    saveCurrentTheme();
  }
  
  /**
   * 切换主题
   */
  function switchTheme(themeId: string) {
    const theme = allThemes.value.find(t => t.id === themeId);
    if (theme) {
      applyTheme(theme);
    }
  }
  
  /**
   * 创建新主题
   */
  function createTheme(name: string, isDark = false): ThemeConfig {
    const theme = createDefaultTheme(name, isDark);
    custom.value.push(theme);
    saveCustomThemes();
    return theme;
  }
  
  /**
   * 更新主题
   */
  function updateTheme(themeId: string, updates: Partial<ThemeConfig>) {
    const index = custom.value.findIndex(t => t.id === themeId);
    if (index !== -1) {
      custom.value[index] = {
        ...custom.value[index],
        ...updates,
        updatedAt: new Date().toISOString(),
      };
      saveCustomThemes();
      
      // 如果是当前主题，重新应用
      if (currentTheme.value.id === themeId) {
        applyTheme(custom.value[index]);
      }
    }
  }
  
  /**
   * 删除主题
   */
  function deleteTheme(themeId: string) {
    const theme = custom.value.find(t => t.id === themeId);
    if (!theme || theme.isBuiltIn) return;
    
    custom.value = custom.value.filter(t => t.id !== themeId);
    saveCustomThemes();
    
    // 如果删除的是当前主题，切换到默认主题
    if (currentTheme.value.id === themeId) {
      applyTheme(lightTheme);
    }
    
    // 删除相关的应用配置
    applications.value = applications.value.filter(a => a.themeId !== themeId);
    saveApplications();
  }
  
  /**
   * 复制主题
   */
  function duplicateTheme(themeId: string): ThemeConfig | null {
    const theme = allThemes.value.find(t => t.id === themeId);
    if (!theme) return null;
    
    const newTheme: ThemeConfig = {
      ...deepClone(theme),
      id: generateThemeId(),
      name: `${theme.name} (副本)`,
      isBuiltIn: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    custom.value.push(newTheme);
    saveCustomThemes();
    return newTheme;
  }
  
  /**
   * 开始编辑主题
   */
  function startEditTheme(themeId: string) {
    const theme = allThemes.value.find(t => t.id === themeId);
    if (theme) {
      // 如果是内置主题，创建副本
      if (theme.isBuiltIn) {
        editingTheme.value = deepClone(theme);
        editingTheme.value.id = generateThemeId();
        editingTheme.value.name = `${theme.name} (自定义)`;
        editingTheme.value.isBuiltIn = false;
      } else {
        editingTheme.value = deepClone(theme);
      }
    }
  }
  
  /**
   * 保存编辑的主题
   */
  function saveEditingTheme() {
    if (!editingTheme.value) return;
    
    const existingIndex = custom.value.findIndex(t => t.id === editingTheme.value!.id);
    
    if (existingIndex !== -1) {
      // 更新现有主题
      custom.value[existingIndex] = {
        ...editingTheme.value,
        updatedAt: new Date().toISOString(),
      };
    } else {
      // 添加新主题
      custom.value.push({
        ...editingTheme.value,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    }
    
    saveCustomThemes();
    
    // 如果是当前主题，重新应用
    if (currentTheme.value.id === editingTheme.value.id) {
      applyTheme(editingTheme.value);
    }
    
    editingTheme.value = null;
  }
  
  /**
   * 取消编辑主题
   */
  function cancelEditTheme() {
    editingTheme.value = null;
  }
  
  /**
   * 应用主题到组件
   */
  function applyThemeToComponent(themeId: string, componentIds: string[]) {
    // 移除这些组件的旧应用
    applications.value = applications.value.filter(app => 
      !(app.scope === 'component' && app.componentIds?.some(id => componentIds.includes(id)))
    );
    
    // 添加新应用
    applications.value.push({
      themeId,
      scope: 'component',
      componentIds,
    });
    
    saveApplications();
  }
  
  /**
   * 移除组件的主题应用
   */
  function removeComponentTheme(componentIds: string[]) {
    applications.value = applications.value.filter(app => 
      !(app.scope === 'component' && app.componentIds?.some(id => componentIds.includes(id)))
    );
    saveApplications();
  }
  
  /**
   * 获取组件的主题
   */
  function getComponentTheme(componentId: string): ThemeConfig {
    return componentThemes.value.get(componentId) || currentTheme.value;
  }
  
  /**
   * 导出主题
   */
  function exportThemeFile(themeId: string) {
    const theme = allThemes.value.find(t => t.id === themeId);
    if (!theme) return;
    
    const blob = exportTheme(theme);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${theme.name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
  
  /**
   * 导入主题
   */
  function importThemeFile(file: File): Promise<ThemeConfig> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const theme = importTheme(e.target?.result as string);
          custom.value.push(theme);
          saveCustomThemes();
          resolve(theme);
        } catch (error) {
          reject(new Error('无效的主题文件'));
        }
      };
      reader.onerror = () => reject(new Error('读取文件失败'));
      reader.readAsText(file);
    });
  }
  
  /**
   * 生成主题缩略图
   */
  function generateThumbnail(themeId: string): string {
    const theme = allThemes.value.find(t => t.id === themeId);
    if (!theme) return '';
    
    if (theme.thumbnail) return theme.thumbnail;
    
    const thumbnail = generateThemeThumbnail(theme);
    
    // 保存缩略图
    if (!theme.isBuiltIn) {
      updateTheme(theme.id, { thumbnail });
    }
    
    return thumbnail;
  }
  
  /**
   * 切换暗黑模式
   */
  function toggleDarkMode() {
    const targetTheme = isDarkMode.value 
      ? lightThemes.value[0] 
      : darkThemes.value[0];
    
    if (targetTheme) {
      applyTheme(targetTheme);
    }
  }
  
  /**
   * 重置为默认主题
   */
  function resetToDefault() {
    applyTheme(lightTheme);
    applications.value = [];
    saveApplications();
  }
  
  /**
   * 获取主题预览样式
   */
  function getThemePreviewStyle(theme: ThemeConfig) {
    return {
      backgroundColor: theme.colors.background,
      color: theme.colors.text,
      borderColor: theme.colors.border,
    };
  }
  
  // 监听当前主题变化
  watch(currentTheme, (theme) => {
    // 更新body类名
    document.body.classList.toggle('dark-mode', theme.isDark);
  }, { immediate: true });
  
  return {
    // State
    builtIn,
    custom,
    currentTheme,
    applications,
    editingTheme,
    isLoading,
    
    // Getters
    allThemes,
    lightThemes,
    darkThemes,
    isDarkMode,
    echartsTheme,
    componentThemes,
    
    // Actions
    initialize,
    applyTheme,
    switchTheme,
    createTheme,
    updateTheme,
    deleteTheme,
    duplicateTheme,
    startEditTheme,
    saveEditingTheme,
    cancelEditTheme,
    applyThemeToComponent,
    removeComponentTheme,
    getComponentTheme,
    exportThemeFile,
    importThemeFile,
    generateThumbnail,
    toggleDarkMode,
    resetToDefault,
    getThemePreviewStyle,
  };
});
