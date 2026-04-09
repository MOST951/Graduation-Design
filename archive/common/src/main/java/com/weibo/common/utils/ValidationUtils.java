package com.weibo.common.utils;

import java.util.regex.Pattern;

/**
 * 数据校验工具类。
 */
public final class ValidationUtils {

    private static final Pattern EMAIL_PATTERN = Pattern.compile("^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,6}$", Pattern.CASE_INSENSITIVE);
    private static final Pattern PHONE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");

    private ValidationUtils() {}

    public static boolean isValidEmail(String email) {
        return email != null && EMAIL_PATTERN.matcher(email).matches();
    }

    public static boolean isValidPhone(String phone) {
        return phone != null && PHONE_PATTERN.matcher(phone).matches();
    }
    
        public static boolean isValidIdCard(String idCard) {
        // This is a simplified check for 18-digit ID cards
        if (idCard == null || idCard.length() != 18) return false;
        return idCard.matches("^\\d{17}(\\d|X)$/i");
    }

    public static boolean isStrongPassword(String password) {
        // At least 8 chars, one uppercase, one lowercase, one digit
        if (password == null || password.length() < 8) return false;
        return password.matches("^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$");
    }
}
