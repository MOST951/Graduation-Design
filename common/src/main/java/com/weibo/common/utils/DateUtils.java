package com.weibo.common.utils;

import com.weibo.common.constants.AppConstants;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;

/**
 * 线程安全的日期时间工具类。
 */
public final class DateUtils {

    private static final ThreadLocal<SimpleDateFormat> DATE_FORMATTER = 
        ThreadLocal.withInitial(() -> new SimpleDateFormat(AppConstants.DATE_FORMAT));

    private static final ThreadLocal<SimpleDateFormat> DATETIME_FORMATTER = 
        ThreadLocal.withInitial(() -> new SimpleDateFormat(AppConstants.DATETIME_FORMAT));

    private DateUtils() {}

    public static String formatDate(Date date) {
        if (date == null) return null;
        return DATETIME_FORMATTER.get().format(date);
    }

    public static Date parseDate(String dateStr) throws ParseException {
        if (StringUtils.isBlank(dateStr)) return null;
        return DATETIME_FORMATTER.get().parse(dateStr);
    }

    public static Date getCurrentDate() {
        return new Date();
    }

    public static Date addDays(Date date, int daysToAdd) {
        Calendar cal = Calendar.getInstance();
        cal.setTime(date);
        cal.add(Calendar.DAY_OF_MONTH, daysToAdd);
        return cal.getTime();
    }

    public static boolean isWeekend(Date date) {
        Calendar cal = Calendar.getInstance();
        cal.setTime(date);
        int dayOfWeek = cal.get(Calendar.DAY_OF_WEEK);
        return dayOfWeek == Calendar.SATURDAY || dayOfWeek == Calendar.SUNDAY;
    }
}
