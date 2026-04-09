// ============================================================
//  Design System v2 — JS/TS Color Constants
//  Mirror of variables.scss for use in <script> sections
//  (ECharts configs, dynamic styles, template bindings, etc.)
// ============================================================

// 主色调
export const PRIMARY = '#165DFF'
export const PRIMARY_LIGHT = '#4080FF'
export const PRIMARY_LIGHTER = '#94BFFF'
export const PRIMARY_BG = '#E8F0FF'
export const PRIMARY_DARK = '#0E42D2'

// 语义色
export const SUCCESS = '#00B42A'
export const SUCCESS_LIGHT = '#AFF0B5'
export const WARNING = '#FF7D00'
export const WARNING_LIGHT = '#FFE4BA'
export const DANGER = '#F53F3F'
export const DANGER_LIGHT = '#FDCDC5'
export const INFO = '#86909C'
export const INFO_LIGHT = '#E5E6EB'

// 中性色
export const TEXT_PRIMARY = '#1D2129'
export const TEXT_REGULAR = '#4E5969'
export const TEXT_SECONDARY = '#86909C'
export const TEXT_PLACEHOLDER = '#C9CDD4'

// 边框色
export const BORDER_BASE = '#E5E6EB'
export const BORDER_LIGHT = '#F2F3F5'

// 背景色
export const BG_WHITE = '#FFFFFF'
export const BG_PAGE = '#F7F8FA'
export const BG_HOVER = '#F7F8FA'

// 图表专用调色板
export const CHART_COLORS = {
  positive: SUCCESS,
  neutral: INFO,
  negative: DANGER,
  primary: PRIMARY,
  warning: WARNING,
}

// ECharts 常用渐变辅助
export const chartGradient = (color: string, opacity1 = 0.3, opacity2 = 0.02) => ({
  type: 'linear' as const,
  x: 0, y: 0, x2: 0, y2: 1,
  colorStops: [
    { offset: 0, color: color.replace('#', 'rgba(') ? `rgba(${parseInt(color.slice(1, 3), 16)},${parseInt(color.slice(3, 5), 16)},${parseInt(color.slice(5, 7), 16)},${opacity1})` : color },
    { offset: 1, color: color.replace('#', 'rgba(') ? `rgba(${parseInt(color.slice(1, 3), 16)},${parseInt(color.slice(3, 5), 16)},${parseInt(color.slice(5, 7), 16)},${opacity2})` : color },
  ],
})
