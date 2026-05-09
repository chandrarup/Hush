import Foundation
import SQLite3

final class HistoryStore {
    private var db: OpaquePointer?
    private let sqliteTransient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

    init() {
        openDatabase()
        createTableIfNeeded()
    }

    deinit {
        sqlite3_close(db)
    }

    private var dbPath: String {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir = base.appendingPathComponent("VoiceFlow", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("history.db").path
    }

    private func openDatabase() {
        sqlite3_open(dbPath, &db)
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
        sqlite3_exec(db, sql, nil, nil, nil)
    }

    @discardableResult
    func save(raw: String, clean: String, level: String, app: String?) -> Int64 {
        let sql = "INSERT INTO entries(ts, raw, clean, level, app) VALUES(?,?,?,?,?);"
        var stmt: OpaquePointer?
        sqlite3_prepare_v2(db, sql, -1, &stmt, nil)
        sqlite3_bind_text(stmt, 1, ns(isoNow), -1, sqliteTransient)
        sqlite3_bind_text(stmt, 2, ns(raw), -1, sqliteTransient)
        sqlite3_bind_text(stmt, 3, ns(clean), -1, sqliteTransient)
        sqlite3_bind_text(stmt, 4, ns(level), -1, sqliteTransient)
        if let app {
            sqlite3_bind_text(stmt, 5, ns(app), -1, sqliteTransient)
        } else {
            sqlite3_bind_null(stmt, 5)
        }
        sqlite3_step(stmt)
        sqlite3_finalize(stmt)
        return sqlite3_last_insert_rowid(db)
    }

    func fetch(limit: Int = 200) -> [HistoryEntry] {
        let sql = "SELECT id, ts, raw, clean, level, app FROM entries ORDER BY id DESC LIMIT ?;"
        var stmt: OpaquePointer?
        sqlite3_prepare_v2(db, sql, -1, &stmt, nil)
        sqlite3_bind_int(stmt, 1, Int32(limit))

        var entries: [HistoryEntry] = []
        while sqlite3_step(stmt) == SQLITE_ROW {
            let id = sqlite3_column_int64(stmt, 0)
            let ts = String(cString: sqlite3_column_text(stmt, 1))
            let raw = String(cString: sqlite3_column_text(stmt, 2))
            let clean = String(cString: sqlite3_column_text(stmt, 3))
            let level = String(cString: sqlite3_column_text(stmt, 4))
            let appName = sqlite3_column_text(stmt, 5).map { String(cString: $0) }
            entries.append(.init(id: id, timestampISO8601: ts, rawText: raw, cleanText: clean, cleanupLevel: level, appName: appName))
        }

        sqlite3_finalize(stmt)
        return entries
    }

    private var isoNow: String {
        ISO8601DateFormatter().string(from: Date())
    }

    private func ns(_ value: String) -> UnsafePointer<Int8>? {
        (value as NSString).utf8String
    }
}
