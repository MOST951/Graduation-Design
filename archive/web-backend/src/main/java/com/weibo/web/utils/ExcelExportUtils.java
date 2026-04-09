package com.weibo.web.utils;

import com.weibo.web.entity.SentimentResult;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.List;

/**
 * Excel导出工具类。
 */
public class ExcelExportUtils {

    public static byte[] exportToExcel(List<SentimentResult> results) throws IOException {
        try (XSSFWorkbook workbook = new XSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            XSSFSheet sheet = workbook.createSheet("Sentiment Analysis Results");

            // 创建表头
            Row headerRow = sheet.createRow(0);
            String[] columns = {"ID", "Content", "Sentiment", "Confidence", "Timestamp"};
            for (int i = 0; i < columns.length; i++) {
                Cell cell = headerRow.createCell(i);
                cell.setCellValue(columns[i]);
            }

            // 填充数据
            int rowNum = 1;
            for (SentimentResult result : results) {
                Row row = sheet.createRow(rowNum++);
                row.createCell(0).setCellValue(result.getId());
                row.createCell(1).setCellValue(result.getContent());
                row.createCell(2).setCellValue(result.getSentiment());
                row.createCell(3).setCellValue(result.getConfidence());
                row.createCell(4).setCellValue(result.getCreatedAt().toString());
            }

            workbook.write(out);
            return out.toByteArray();
        }
    }
}
