package com.weibo.collector.storage;

import com.weibo.common.config.HdfsConfig;
import lombok.extern.slf4j.Slf4j;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FSDataOutputStream;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.IOException;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;

/**
 * Handles writing data to the Hadoop Distributed File System (HDFS).
 * <p>
 * This class provides a simple interface for appending data to a file in HDFS,
 * which is useful for storing raw collected data.
 * </p>
 */
@Slf4j
@Component
public class HdfsDataWriter {

    @Autowired
    private HdfsConfig hdfsConfig;

    private FileSystem fileSystem;

    /**
     * Initializes the HDFS file system client.
     */
    @PostConstruct
    public void init() {
        try {
            Configuration config = new Configuration();
            fileSystem = FileSystem.get(URI.create(hdfsConfig.getDefaultFS()), config);
            log.info("HDFS FileSystem initialized successfully.");
        } catch (IOException e) {
            log.error("Failed to initialize HDFS FileSystem", e);
        }
    }

    /**
     * Appends a line of data to the specified file in HDFS.
     *
     * @param filePath The path to the file in HDFS.
     * @param data     The string data to append.
     */
        public void appendToHdfs(String filePath, String data) {
        write(filePath, data);
    }

    public List<String> listFiles(String dirPath) throws IOException {
        List<String> fileList = new ArrayList<>();
        Path path = new Path(dirPath);
        if (fileSystem.exists(path) && fileSystem.isDirectory(path)) {
            for (FileStatus status : fileSystem.listStatus(path)) {
                fileList.add(status.getPath().toString());
            }
        }
        return fileList;
    }

    /**
     * Writes data to the specified file in HDFS.
     *
     * @param filePath The path to the file in HDFS.
     * @param data     The string data to write.
     */
    public void writeToHdfs(String filePath, String data) {
        Path path = new Path(filePath);
        try (FSDataOutputStream outputStream = fileSystem.exists(path) ? fileSystem.append(path) : fileSystem.create(path)) {
            outputStream.writeUTF(data + "\n");
        } catch (IOException e) {
            log.error("Failed to write to HDFS file: {}", filePath, e);
        }
    }
}
