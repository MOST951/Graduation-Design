// utils/formatter.ts

/**
 * 格式化数字，添加千位分隔符
 * @param num 数字
 * @returns 格式化后的字符串
 */
export function formatNumber(num: number | string): string {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * 格式化时间为 HH:mm:ss
 * @param date Date对象或时间戳
 * @returns 格式化后的时间字符串
 */
export function formatTime(date: Date | number | string): string {
  const d = new Date(date);
  return d.toLocaleTimeString();
}
