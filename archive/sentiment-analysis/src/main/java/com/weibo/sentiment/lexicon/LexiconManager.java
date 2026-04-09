package com.weibo.sentiment.lexicon;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.sql.Connection; // JDBC placeholder
import java.sql.PreparedStatement; // JDBC placeholder
import java.sql.ResultSet; // JDBC placeholder
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * Manages the lifecycle of sentiment lexicons, including dynamic loading, updating, persistence, and hot-reloading.
 * This class is designed to be thread-safe.
 */
@Component
public class LexiconManager {

    // The default domain for the base lexicon
    public static final String BASE_DOMAIN = "base";

    // Holds all lexicons, keyed by domain name (e.g., "base", "finance", "sports").
    private final Map<String, ManagedLexicon> domainLexicons = new ConcurrentHashMap<>();

    // A lock to ensure thread-safe read/write operations on the lexicons.
    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

    // For hot-reloading from the filesystem.
    private final ExecutorService watchServiceExecutor = Executors.newSingleThreadExecutor();
    private final Path lexiconDirectory;

    /**
     * Constructor for the LexiconManager.
     *
     * @param lexiconDirectoryPath The path to the directory where lexicon files are stored.
     */
        @Autowired
    public LexiconManager(AnalysisProperties properties) {
        String lexiconDirectoryPath = properties.getLexiconPath();
        this.lexiconDirectory = Paths.get(lexiconDirectoryPath);
        if (!Files.exists(this.lexiconDirectory)) {
            try {
                Files.createDirectories(this.lexiconDirectory);
            } catch (IOException e) {
                throw new RuntimeException("Failed to create lexicon directory", e);
            }
        }
        loadAllLexiconsFromDirectory();
        startWatchingDirectory();
    }

    /**
     * Gets a combined, immutable lexicon for a specific domain, overlaying the base lexicon.
     * This is the primary method for a calculator to get its required lexicon.
     *
     * @param domain The domain for which to get the lexicon (e.g., "finance").
     * @return An immutable SentimentLexicon instance ready for calculation.
     */
    public SentimentLexicon getLexiconForDomain(String domain) {
        lock.readLock().lock();
        try {
            ManagedLexicon baseLexicon = domainLexicons.get(BASE_DOMAIN);
            ManagedLexicon domainLexicon = domainLexicons.get(domain);

            // Create a new merged lexicon instance
                        SentimentLexicon mergedLexicon = new SentimentLexicon();
            mergedLexicon.loadFromManaged(baseLexicon, domainLexicon);
            return mergedLexicon;
        } finally {
            lock.readLock().unlock();
        }
    }

    // --- Dynamic Management Methods ---

    public void addWord(String domain, WordType type, String word, double score) {
        lock.writeLock().lock();
        try {
            ManagedLexicon lexicon = domainLexicons.computeIfAbsent(domain, k -> new ManagedLexicon());
            lexicon.addWord(type, word, score);
        } finally {
            lock.writeLock().unlock();
        }
    }

    public void removeWord(String domain, String word) {
        lock.writeLock().lock();
        try {
            ManagedLexicon lexicon = domainLexicons.get(domain);
            if (lexicon != null) {
                lexicon.removeWord(word);
            }
        } finally {
            lock.writeLock().unlock();
        }
    }

    // --- Persistence Methods ---

    public void exportLexiconToFile(String domain) throws IOException {
        lock.readLock().lock();
        try {
            ManagedLexicon lexicon = domainLexicons.get(domain);
            if (lexicon == null) {
                throw new IllegalArgumentException("Domain not found: " + domain);
            }
            // Persist each word type to its corresponding file, e.g., finance_positive.txt
            lexicon.persistToFiles(lexiconDirectory, domain);
        } finally {
            lock.readLock().unlock();
        }
    }

    public void saveToDatabase(String domain, Connection conn) throws Exception {
        // Placeholder for database persistence logic
        // This would involve JDBC/JPA to write lexicon data to tables.
        // Example: INSERT INTO lexicons (domain, word, type, score) VALUES (?, ?, ?, ?)
        System.out.println("Database persistence not implemented.");
    }

    // --- Hot-Reloading Logic ---

    private void startWatchingDirectory() {
        watchServiceExecutor.submit(() -> {
            try (WatchService watchService = FileSystems.getDefault().newWatchService()) {
                lexiconDirectory.register(watchService, StandardWatchEventKinds.ENTRY_CREATE, StandardWatchEventKinds.ENTRY_MODIFY);
                System.out.println("Started watching lexicon directory: " + lexiconDirectory);

                WatchKey key;
                while ((key = watchService.take()) != null) {
                    for (WatchEvent<?> event : key.pollEvents()) {
                        Path changedFile = (Path) event.context();
                        System.out.println("Detected change in: " + changedFile);
                        reloadLexiconFromFile(changedFile.toString());
                    }
                    key.reset();
                }
            } catch (IOException | InterruptedException e) {
                e.printStackTrace();
            }
        });
    }

    private void loadAllLexiconsFromDirectory() {
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(lexiconDirectory, "*.txt")) {
            for (Path entry : stream) {
                reloadLexiconFromFile(entry.getFileName().toString());
            }
        } catch (IOException e) {
            System.err.println("Error loading initial lexicons from directory.");
            e.printStackTrace();
        }
    }

    private void reloadLexiconFromFile(String fileName) {
        // File name format: {domain}_{wordType}.txt (e.g., base_positive.txt, finance_degree.txt)
        String[] parts = fileName.replace(".txt", "").split("_");
        if (parts.length != 2) return; // Ignore invalid file names

        String domain = parts[0];
        String typeStr = parts[1];
        WordType type = WordType.fromString(typeStr);
        if (type == null) return;

        Path filePath = lexiconDirectory.resolve(fileName);

        lock.writeLock().lock();
        try {
            System.out.println("Reloading domain '" + domain + "' for type '" + type + "' from file " + fileName);
            ManagedLexicon lexicon = domainLexicons.computeIfAbsent(domain, k -> new ManagedLexicon());
            lexicon.loadFile(filePath, type);
        } catch (IOException e) {
            System.err.println("Failed to reload lexicon file: " + fileName);
            e.printStackTrace();
        } finally {
            lock.writeLock().unlock();
        }
    }

    public void shutdown() {
        watchServiceExecutor.shutdownNow();
    }

    // --- Inner class for a mutable lexicon ---

    public enum WordType {
        POSITIVE, NEGATIVE, DEGREE, NEGATION, CONJUNCTION;

        public static WordType fromString(String s) {
            try {
                return WordType.valueOf(s.toUpperCase());
            } catch (IllegalArgumentException e) {
                return null;
            }
        }
    }

    /**
     * Represents a mutable lexicon for a single domain.
     */
    private static class ManagedLexicon {
        final Map<String, Double> sentimentWords = new ConcurrentHashMap<>();
        final Map<String, Double> degreeAdverbs = new ConcurrentHashMap<>();
        final Set<String> negationWords = ConcurrentHashMap.newKeySet();
        final Set<String> conjunctions = ConcurrentHashMap.newKeySet();

        void addWord(WordType type, String word, double score) {
            switch (type) {
                case POSITIVE: sentimentWords.put(word, Math.abs(score)); break;
                case NEGATIVE: sentimentWords.put(word, -Math.abs(score)); break;
                case DEGREE: degreeAdverbs.put(word, score); break;
                case NEGATION: negationWords.add(word); break;
                case CONJUNCTION: conjunctions.add(word); break;
            }
        }

        void removeWord(String word) {
            sentimentWords.remove(word);
            degreeAdverbs.remove(word);
            negationWords.remove(word);
            conjunctions.remove(word);
        }

        void loadFile(Path filePath, WordType type) throws IOException {
            // Clear previous entries for this type before loading
            clearType(type);
            try (BufferedReader reader = Files.newBufferedReader(filePath, StandardCharsets.UTF_8)) {
                String line;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty()) continue;

                    String[] parts = line.split("\\s+");
                    String word = parts[0];
                    double score = 1.0;
                    if (parts.length > 1) {
                        try { score = Double.parseDouble(parts[1]); } catch (NumberFormatException ignored) {}
                    }

                    addWord(type, word, score);
                }
            }
        }

        void persistToFiles(Path directory, String domain) throws IOException {
            // Example for positive words
            persistMap(directory.resolve(domain + "_positive.txt"), sentimentWords, e -> e.getValue() > 0);
            // ... implement for other types
        }

                private void persistMap(Path path, Map<String, Double> map, java.util.function.Predicate<Map.Entry<String, Double>> filter) throws IOException {
            try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
                for (Map.Entry<String, Double> entry : map.entrySet()) {
                    if (filter.test(entry)) {
                        writer.write(entry.getKey() + "\t" + entry.getValue());
                        writer.newLine();
                    }
                }
            }
        }

        private void persistSet(Path path, Set<String> set) throws IOException {
            try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
                for (String item : set) {
                    writer.write(item);
                    writer.newLine();
                }
            }
        }
            try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
                for (Object item : set) {
                    if (filter.test(item)) {
                        // Logic to format and write item
                        writer.write(item.toString());
                        writer.newLine();
                    }
                }
            }
        }

        private void clearType(WordType type) {
            switch (type) {
                case POSITIVE: sentimentWords.entrySet().removeIf(e -> e.getValue() > 0); break;
                case NEGATIVE: sentimentWords.entrySet().removeIf(e -> e.getValue() < 0); break;
                case DEGREE: degreeAdverbs.clear(); break;
                case NEGATION: negationWords.clear(); break;
                case CONJUNCTION: conjunctions.clear(); break;
            }
        }
    }
}
