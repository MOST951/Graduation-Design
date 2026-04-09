package com.weibo.collector.storage;

import org.springframework.stereotype.Component;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;

/**
 * 本地数据备份器
 */
@Component
public class LocalDataBackup {

    private static final String BACKUP_DIR = "backups/";

    public void backupData(String fileName, String content) throws IOException {
        Files.write(Paths.get(BACKUP_DIR + fileName), content.getBytes());
    }

    public String restoreData(String fileName) throws IOException {
        return new String(Files.readAllBytes(Paths.get(BACKUP_DIR + fileName)));
    }

    public void cleanupOldBackups(long daysOld) {
        // Logic to delete files older than 'daysOld'
    }
}
