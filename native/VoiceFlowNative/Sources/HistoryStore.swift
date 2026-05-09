import Foundation
import SQLite3
import OSLog

final class HistoryStore {
    private var db: OpaquePointer?
    private let sqliteTransient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
    private let logger = Logger(subsystem: "com.voiceflow.app", category: "HistoryStore")

    init() {
        openDatabase()
        createTableIfNeeded()
    }

    deinit {
        sqlite3_close(db)
    }

    private var dbPath: String {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support", isDirectory: true)
        let dir = base.appendingPathComponent("VoiceFlow", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("history.db").path
    }

    private func openDatabase() {
        let rc = sqlite3_open(dbPath, &db)
        if rc != SQLITE_OK {
            let msg = db.flatMap { sqlite3_errmsg($0) }.map { String(cString: $0) } ?? "unknown sqlite error"
            logger.error("sqlite open failed: \(msg)")
        }
    }

    private func createTableIfNeeded() {
        let sql = """
        CREATE TABLE IF NOT EXISTS entries (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts TEXT NOT NULL,
          raw TEXT NOT NULL,
          clean TEXT NOT NULL,
          level TEXT NOT NULL,
          app TEXT
        );
        """
        let rc = sqlite3_exec(db, sql, nil, nil, nil)
        if rc != SQLITE_OK {
            let msg = db.flatMap { sqlite3_errmsg($0) }.map { String(cString: $0) } ?? "unknown sqlite error"
            logger.error("sqlite schema init failed: \(msg)")
        }
    }

    @discardableResult
    func save(raw: String, clean: String, level: String, app: String?) -> Int64 {
        let sql = "INSERT INTO entries(ts, raw, clean, level, app) VALUES(?,?,?,?,?);"
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            logger.error("sqlite prepare failed for insert")
            return -1
        }
        guard sqlite3_bind_text(stmt, 1, toCString(isoNow), -1, sqliteTransient) == SQLITE_OK,
              sqlite3_bind_text(stmt, 2, toCString(raw), -1, sqliteTransient) == SQLITE_OK,
              sqlite3_bind_text(stmt, 3, toCString(clean), -1, sqliteTransient) == SQLITE_OK,
              sqlite3_bind_text(stmt, 4, toCString(level), -1, sqliteTransient) == SQLITE_OK else {
            logger.error("sqlite bind failed for insert")
            sqlite3_finalize(stmt)
            return -1
        }
        if let app {
            guard sqlite3_bind_text(stmt, 5, toCString(app), -1, sqliteTransient) == SQLITE_OK else {
                logger.error("sqlite bind failed for app column")
                sqlite3_finalize(stmt)
                return -1
            }
        } else {
            sqlite3_bind_null(stmt, 5)
        }
        guard sqlite3_step(stmt) == SQLITE_DONE else {
            logger.error("sqlite step failed for insert")
            sqlite3_finalize(stmt)
            return -1
        }
        sqlite3_finalize(stmt)
        return sqlite3_last_insert_rowid(db)
    }

    func fetch(limit: Int = 200) -> [HistoryEntry] {
        let sql = "SELECT id, ts, raw, clean, level, app FROM entries ORDER BY id DESC LIMIT ?;"
        var stmt: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK else {
            logger.error("sqlite prepare failed for fetch")
            return []
        }
        guard sqlite3_bind_int(stmt, 1, Int32(limit)) == SQLITE_OK else {
            logger.error("sqlite bind failed for fetch limit")
            sqlite3_finalize(stmt)
            return []
        }

        var entries: [HistoryEntry] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            let id = sqlite3_column_int64(stmt, 0)
            guard let tsPtr = sqlite3_column_text(stmt, 1),
                  let rawPtr = sqlite3_column_text(stmt, 2),
                  let cleanPtr = sqlite3_column_text(stmt, 3),
                  let levelPtr = sqlite3_column_text(stmt, 4) else {
                continue
            }
            let ts = String(cString: tsPtr)
            let raw = String(cString: rawPtr)
            let clean = String(cString: cleanPtr)
            let level = String(cString: levelPtr)
            let appName = sqlite3_column_text(stmt, 5).map { String(cString: $0) }
            entries.append(.init(id: id, timestampISO8601: ts, rawText: raw, cleanText: clean, cleanupLevel: level, appName: appName))
        }

        sqlite3_finalize(stmt)
        return entries
    }

    private var isoNow: String {
        ISO8601DateFormatter().string(from: Date())
    }

    private func toCString(_ value: String) -> UnsafePointer<Int8>? {
        (value as NSString).utf8String
    }
}
