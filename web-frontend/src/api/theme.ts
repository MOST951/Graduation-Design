/**
 * 可视化主题管理 API
 */
import { PRIMARY, PRIMARY_LIGHT, SUCCESS, WARNING, DANGER, INFO, TEXT_PRIMARY, TEXT_REGULAR, TEXT_PLACEHOLDER, BORDER_BASE } from '@/styles/colors';

// ==================== 类型定义 ====================

/** 颜色方案 */
export interface ColorScheme {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  danger: string;
  info: string;
  background: string;
  backgroundSecondary: string;
  surface: string;
  text: string;
  textSecondary: string;
  textDisabled: string;
  border: string;
  borderLight: string;
  divider: string;
}

/** 图表配色 */
export interface ChartColors {
  series: string[];
  positive: string;
  negative: string;
  neutral: string;
  gradient: {
    start: string;
    end: string;
  }[];
}

/** 字体配置 */
export interface FontConfig {
  family: string;
  familySecondary?: string;
  size: {
    xs: number;
    sm: number;
    base: number;
    lg: number;
    xl: number;
    xxl: number;
  };
  weight: {
    light: number;
    normal: number;
    medium: number;
    semibold: number;
    bold: number;
  };
  lineHeight: {
    tight: number;
    normal: number;
    relaxed: number;
  };
}

/** 间距系统 */
export interface SpacingSystem {
  xs: number;
  sm: number;
  md: number;
  lg: number;
  xl: number;
  xxl: number;
}

/** 效果配置 */
export interface EffectConfig {
  shadow: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  borderRadius: {
    sm: number;
    md: number;
    lg: number;
    xl: number;
    full: number;
  };
  borderWidth: {
    thin: number;
    normal: number;
    thick: number;
  };
  animation: {
    duration: {
      fast: number;
      normal: number;
      slow: number;
    };
    easing: {
      linear: string;
      ease: string;
      easeIn: string;
      easeOut: string;
      easeInOut: string;
    };
  };
}

/** 主题配置 */
export interface ThemeConfig {
  id: string;
  name: string;
  description?: string;
  thumbnail?: string;
  isBuiltIn: boolean;
  isDark: boolean;
  colors: ColorScheme;
  chartColors: ChartColors;
  fonts: FontConfig;
  spacing: SpacingSystem;
  effects: EffectConfig;
  createdAt: string;
  updatedAt: string;
}

/** 主题应用范围 */
export type ThemeScope = 'global' | 'component';

/** 主题应用配置 */
export interface ThemeApplication {
  themeId: string;
  scope: ThemeScope;
  componentIds?: string[];
}

// ==================== 内置主题 ====================

/** 明亮主题 */
export const lightTheme: ThemeConfig = {
  id: 'light',
  name: '明亮主题',
  description: '清新明亮的默认主题',
  isBuiltIn: true,
  isDark: false,
  colors: {
    primary: PRIMARY,
    secondary: INFO,
    success: SUCCESS,
    warning: WARNING,
    danger: DANGER,
    info: INFO,
    background: '#FFFFFF',
    backgroundSecondary: '#F5F7FA',
    surface: '#FFFFFF',
    text: TEXT_PRIMARY,
    textSecondary: TEXT_REGULAR,
    textDisabled: TEXT_PLACEHOLDER,
    border: BORDER_BASE,
    borderLight: '#E4E7ED',
    divider: '#EBEEF5',
  },
  chartColors: {
    series: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'],
    positive: SUCCESS,
    negative: DANGER,
    neutral: INFO,
    gradient: [
      { start: PRIMARY, end: PRIMARY_LIGHT },
      { start: SUCCESS, end: '#85CE61' },
      { start: WARNING, end: '#EBB563' },
    ],
  },
  fonts: {
    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    size: {
      xs: 12,
      sm: 13,
      base: 14,
      lg: 16,
      xl: 18,
      xxl: 24,
    },
    weight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.8,
    },
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  effects: {
    shadow: {
      sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
      md: '0 2px 8px rgba(0, 0, 0, 0.1)',
      lg: '0 4px 16px rgba(0, 0, 0, 0.15)',
      xl: '0 8px 32px rgba(0, 0, 0, 0.2)',
    },
    borderRadius: {
      sm: 2,
      md: 4,
      lg: 8,
      xl: 16,
      full: 9999,
    },
    borderWidth: {
      thin: 1,
      normal: 2,
      thick: 4,
    },
    animation: {
      duration: {
        fast: 150,
        normal: 300,
        slow: 500,
      },
      easing: {
        linear: 'linear',
        ease: 'ease',
        easeIn: 'ease-in',
        easeOut: 'ease-out',
        easeInOut: 'ease-in-out',
      },
    },
  },
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

/** 暗黑主题 */
export const darkTheme: ThemeConfig = {
  id: 'dark',
  name: '暗黑主题',
  description: '护眼的暗色主题',
  isBuiltIn: true,
  isDark: true,
  colors: {
    primary: PRIMARY,
    secondary: INFO,
    success: SUCCESS,
    warning: WARNING,
    danger: DANGER,
    info: INFO,
    background: '#1A1A1A',
    backgroundSecondary: '#2C2C2C',
    surface: '#252525',
    text: '#E5E5E5',
    textSecondary: '#B3B3B3',
    textDisabled: '#666666',
    border: '#404040',
    borderLight: '#333333',
    divider: '#2A2A2A',
  },
  chartColors: {
    series: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'],
    positive: SUCCESS,
    negative: DANGER,
    neutral: INFO,
    gradient: [
      { start: PRIMARY, end: PRIMARY_LIGHT },
      { start: SUCCESS, end: '#85CE61' },
      { start: WARNING, end: '#EBB563' },
    ],
  },
  fonts: lightTheme.fonts,
  spacing: lightTheme.spacing,
  effects: {
    ...lightTheme.effects,
    shadow: {
      sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
      md: '0 2px 8px rgba(0, 0, 0, 0.4)',
      lg: '0 4px 16px rgba(0, 0, 0, 0.5)',
      xl: '0 8px 32px rgba(0, 0, 0, 0.6)',
    },
  },
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

/** 科技蓝主题 */
export const techBlueTheme: ThemeConfig = {
  id: 'tech-blue',
  name: '科技蓝',
  description: '现代科技感的蓝色主题',
  isBuiltIn: true,
  isDark: true,
  colors: {
    primary: '#00D4FF',
    secondary: '#0099CC',
    success: '#00E676',
    warning: '#FFD600',
    danger: '#FF5252',
    info: '#00B8D4',
    background: '#0A1929',
    backgroundSecondary: '#132F4C',
    surface: '#1E3A5F',
    text: '#E3F2FD',
    textSecondary: '#B3E5FC',
    textDisabled: '#546E7A',
    border: '#1E4976',
    borderLight: '#2C5F8D',
    divider: '#1A3A52',
  },
  chartColors: {
    series: ['#00D4FF', '#00E676', '#FFD600', '#FF5252', '#B388FF', '#00B8D4', '#64FFDA', '#FF6E40', '#FFAB40'],
    positive: '#00E676',
    negative: '#FF5252',
    neutral: '#00B8D4',
    gradient: [
      { start: '#00D4FF', end: '#0099CC' },
      { start: '#00E676', end: '#00C853' },
      { start: '#FFD600', end: '#FFC400' },
    ],
  },
  fonts: lightTheme.fonts,
  spacing: lightTheme.spacing,
  effects: {
    ...lightTheme.effects,
    shadow: {
      sm: '0 1px 2px rgba(0, 212, 255, 0.2)',
      md: '0 2px 8px rgba(0, 212, 255, 0.3)',
      lg: '0 4px 16px rgba(0, 212, 255, 0.4)',
      xl: '0 8px 32px rgba(0, 212, 255, 0.5)',
    },
  },
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

/** 商务灰主题 */
export const businessGrayTheme: ThemeConfig = {
  id: 'business-gray',
  name: '商务灰',
  description: '专业稳重的商务主题',
  isBuiltIn: true,
  isDark: false,
  colors: {
    primary: '#5C6BC0',
    secondary: '#78909C',
    success: '#66BB6A',
    warning: '#FFA726',
    danger: '#EF5350',
    info: '#78909C',
    background: '#FAFAFA',
    backgroundSecondary: '#F5F5F5',
    surface: '#FFFFFF',
    text: '#212121',
    textSecondary: '#616161',
    textDisabled: '#9E9E9E',
    border: '#E0E0E0',
    borderLight: '#EEEEEE',
    divider: '#F5F5F5',
  },
  chartColors: {
    series: ['#5C6BC0', '#78909C', '#66BB6A', '#FFA726', '#EF5350', '#42A5F5', '#AB47BC', '#26A69A', '#FF7043'],
    positive: '#66BB6A',
    negative: '#EF5350',
    neutral: '#78909C',
    gradient: [
      { start: '#5C6BC0', end: '#7986CB' },
      { start: '#66BB6A', end: '#81C784' },
      { start: '#FFA726', end: '#FFB74D' },
    ],
  },
  fonts: {
    ...lightTheme.fonts,
    family: 'Georgia, "Times New Roman", serif',
  },
  spacing: lightTheme.spacing,
  effects: lightTheme.effects,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

/** 清新绿主题 */
export const freshGreenTheme: ThemeConfig = {
  id: 'fresh-green',
  name: '清新绿',
  description: '自然清新的绿色主题',
  isBuiltIn: true,
  isDark: false,
  colors: {
    primary: '#4CAF50',
    secondary: '#8BC34A',
    success: '#66BB6A',
    warning: '#FFA726',
    danger: '#EF5350',
    info: '#26A69A',
    background: '#F1F8E9',
    backgroundSecondary: '#E8F5E9',
    surface: '#FFFFFF',
    text: '#1B5E20',
    textSecondary: '#388E3C',
    textDisabled: '#A5D6A7',
    border: '#C8E6C9',
    borderLight: '#DCEDC8',
    divider: '#E8F5E9',
  },
  chartColors: {
    series: ['#4CAF50', '#8BC34A', '#CDDC39', '#FFC107', '#FF9800', '#66BB6A', '#9CCC65', '#D4E157', '#FFEB3B'],
    positive: '#66BB6A',
    negative: '#EF5350',
    neutral: '#8BC34A',
    gradient: [
      { start: '#4CAF50', end: '#66BB6A' },
      { start: '#8BC34A', end: '#9CCC65' },
      { start: '#CDDC39', end: '#D4E157' },
    ],
  },
  fonts: lightTheme.fonts,
  spacing: lightTheme.spacing,
  effects: lightTheme.effects,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

/** 内置主题列表 */
export const builtInThemes: ThemeConfig[] = [
  lightTheme,
  darkTheme,
  techBlueTheme,
  businessGrayTheme,
  freshGreenTheme,
];

// ==================== 工具函数 ====================

/**
 * 生成主题ID
 */
export function generateThemeId(): string {
  return `theme-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * 创建默认主题
 */
export function createDefaultTheme(name: string, isDark = false): ThemeConfig {
  const baseTheme = isDark ? darkTheme : lightTheme;
  return {
    ...baseTheme,
    id: generateThemeId(),
    name,
    description: '',
    isBuiltIn: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

/**
 * 应用主题到CSS变量
 */
export function applyThemeToCSS(theme: ThemeConfig): void {
  const root = document.documentElement;
  
  // 颜色
  Object.entries(theme.colors).forEach(([key, value]) => {
    root.style.setProperty(`--color-${kebabCase(key)}`, value);
  });
  
  // 字体
  root.style.setProperty('--font-family', theme.fonts.family);
  if (theme.fonts.familySecondary) {
    root.style.setProperty('--font-family-secondary', theme.fonts.familySecondary);
  }
  
  Object.entries(theme.fonts.size).forEach(([key, value]) => {
    root.style.setProperty(`--font-size-${key}`, `${value}px`);
  });
  
  Object.entries(theme.fonts.weight).forEach(([key, value]) => {
    root.style.setProperty(`--font-weight-${key}`, String(value));
  });
  
  Object.entries(theme.fonts.lineHeight).forEach(([key, value]) => {
    root.style.setProperty(`--line-height-${key}`, String(value));
  });
  
  // 间距
  Object.entries(theme.spacing).forEach(([key, value]) => {
    root.style.setProperty(`--spacing-${key}`, `${value}px`);
  });
  
  // 效果
  Object.entries(theme.effects.shadow).forEach(([key, value]) => {
    root.style.setProperty(`--shadow-${key}`, value);
  });
  
  Object.entries(theme.effects.borderRadius).forEach(([key, value]) => {
    root.style.setProperty(`--radius-${key}`, `${value}px`);
  });
  
  Object.entries(theme.effects.borderWidth).forEach(([key, value]) => {
    root.style.setProperty(`--border-${key}`, `${value}px`);
  });
  
  Object.entries(theme.effects.animation.duration).forEach(([key, value]) => {
    root.style.setProperty(`--duration-${key}`, `${value}ms`);
  });
}

/**
 * 将主题应用到ECharts配置
 */
export function applyThemeToECharts(theme: ThemeConfig): any {
  return {
    color: theme.chartColors.series,
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: theme.fonts.family,
      fontSize: theme.fonts.size.base,
      color: theme.colors.text,
    },
    title: {
      textStyle: {
        color: theme.colors.text,
        fontSize: theme.fonts.size.xl,
        fontWeight: theme.fonts.weight.semibold,
      },
      subtextStyle: {
        color: theme.colors.textSecondary,
        fontSize: theme.fonts.size.sm,
      },
    },
    legend: {
      textStyle: {
        color: theme.colors.text,
        fontSize: theme.fonts.size.sm,
      },
    },
    tooltip: {
      backgroundColor: theme.colors.surface,
      borderColor: theme.colors.border,
      textStyle: {
        color: theme.colors.text,
        fontSize: theme.fonts.size.sm,
      },
    },
    axisPointer: {
      lineStyle: {
        color: theme.colors.border,
      },
      crossStyle: {
        color: theme.colors.border,
      },
    },
    categoryAxis: {
      axisLine: {
        lineStyle: {
          color: theme.colors.border,
        },
      },
      axisTick: {
        lineStyle: {
          color: theme.colors.border,
        },
      },
      axisLabel: {
        color: theme.colors.textSecondary,
        fontSize: theme.fonts.size.sm,
      },
      splitLine: {
        lineStyle: {
          color: theme.colors.divider,
        },
      },
    },
    valueAxis: {
      axisLine: {
        lineStyle: {
          color: theme.colors.border,
        },
      },
      axisTick: {
        lineStyle: {
          color: theme.colors.border,
        },
      },
      axisLabel: {
        color: theme.colors.textSecondary,
        fontSize: theme.fonts.size.sm,
      },
      splitLine: {
        lineStyle: {
          color: theme.colors.divider,
        },
      },
    },
  };
}

/**
 * 导出主题为JSON
 */
export function exportTheme(theme: ThemeConfig): Blob {
  const json = JSON.stringify(theme, null, 2);
  return new Blob([json], { type: 'application/json' });
}

/**
 * 从JSON导入主题
 */
export function importTheme(json: string): ThemeConfig {
  const theme = JSON.parse(json) as ThemeConfig;
  theme.id = generateThemeId();
  theme.isBuiltIn = false;
  theme.createdAt = new Date().toISOString();
  theme.updatedAt = new Date().toISOString();
  return theme;
}

/**
 * 生成主题缩略图数据URL
 */
export function generateThemeThumbnail(theme: ThemeConfig): string {
  const canvas = document.createElement('canvas');
  canvas.width = 200;
  canvas.height = 120;
  const ctx = canvas.getContext('2d');
  
  if (!ctx) return '';
  
  // 背景
  ctx.fillStyle = theme.colors.background;
  ctx.fillRect(0, 0, 200, 120);
  
  // 主色块
  ctx.fillStyle = theme.colors.primary;
  ctx.fillRect(10, 10, 60, 40);
  
  // 成功色块
  ctx.fillStyle = theme.colors.success;
  ctx.fillRect(80, 10, 60, 40);
  
  // 警告色块
  ctx.fillStyle = theme.colors.warning;
  ctx.fillRect(150, 10, 40, 40);
  
  // 图表色系
  theme.chartColors.series.slice(0, 5).forEach((color, i) => {
    ctx.fillStyle = color;
    ctx.fillRect(10 + i * 38, 60, 35, 50);
  });
  
  return canvas.toDataURL();
}

/**
 * 转换为kebab-case
 */
function kebabCase(str: string): string {
  return str.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
}

/**
 * 混合两个颜色
 */
export function mixColors(color1: string, color2: string, weight: number): string {
  const hex = (x: number) => {
    const h = x.toString(16);
    return h.length === 1 ? '0' + h : h;
  };
  
  const parseColor = (color: string) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(color);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16),
    } : null;
  };
  
  const c1 = parseColor(color1);
  const c2 = parseColor(color2);
  
  if (!c1 || !c2) return color1;
  
  const w = weight / 100;
  const r = Math.round(c1.r * (1 - w) + c2.r * w);
  const g = Math.round(c1.g * (1 - w) + c2.g * w);
  const b = Math.round(c1.b * (1 - w) + c2.b * w);
  
  return `#${hex(r)}${hex(g)}${hex(b)}`;
}
