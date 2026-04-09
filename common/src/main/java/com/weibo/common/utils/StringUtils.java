package com.weibo.common.utils;

import java.util.Arrays;
import java.util.stream.Collectors;

/**
 * 字符串操作工具类。
 */
public final class StringUtils {

    private StringUtils() {}

    public static boolean isBlank(String str) {
        return str == null || str.trim().isEmpty();
    }

    public static boolean isNotBlank(String str) {
        return !isBlank(str);
    }

    public static String trim(String str) {
        return str == null ? null : str.trim();
    }

    public static String join(Object[] array, String separator) {
        if (array == null) return null;
        return Arrays.stream(array).map(String::valueOf).collect(Collectors.joining(separator));
    }

    public static String[] split(String str, String separator) {
        if (str == null) return null;
        return str.split(separator);
    }

    public static String camelToSnake(String str) {
        if (isBlank(str)) return "";
        return str.replaceAll("([a-z0-9])([A-Z])", "$1_$2").toLowerCase();
    }

    public static String snakeToCamel(String str) {
        if (isBlank(str)) return "";
        StringBuilder sb = new StringBuilder();
        boolean toUpperCase = false;
        for (char c : str.toCharArray()) {
            if (c == '_') {
                toUpperCase = true;
            } else {
                sb.append(toUpperCase ? Character.toUpperCase(c) : c);
                toUpperCase = false;
            }
        }
        return sb.toString();
    }
}
