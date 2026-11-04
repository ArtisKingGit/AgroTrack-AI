"""
AgroTrack AI Persistent Database Layer
Provides multi-worker safe, ACID persistent storage using SQLite in Write-Ahead Logging (WAL) mode.
Guarantees data survives process restarts, server crashes, and container redeployments.
"""

import os
import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("agrotrack.database")

# Database Path
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "agrotrack.db")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Creates and configures a SQLite connection with Write-Ahead Logging (WAL) mode.
    WAL allows multiple concurrent readers and serialized writers without locking collisions.
    """
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Configure WAL and performance pragma
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DB_PATH):
    """
    Initializes all core platform tables with indexed columns and JSON document storage.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    cur.executescript("""
    -- Organisations
    CREATE TABLE IF NOT EXISTS organisations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT,
        tier TEXT,
        country TEXT,
        currency TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    -- Organisation Members
    CREATE TABLE IF NOT EXISTS organisation_members (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL,
        status TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_members_org ON organisation_members(org_id);
    CREATE INDEX IF NOT EXISTS idx_members_user ON organisation_members(user_id);

    -- Farmers
    CREATE TABLE IF NOT EXISTS farmers (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        farmer_code TEXT,
        national_id TEXT,
        first_name TEXT,
        last_name TEXT,
        phone TEXT,
        status TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_farmers_org ON farmers(org_id);
    CREATE INDEX IF NOT EXISTS idx_farmers_code ON farmers(farmer_code);
    CREATE INDEX IF NOT EXISTS idx_farmers_status ON farmers(status);

    -- Farms
    CREATE TABLE IF NOT EXISTS farms (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        farmer_id TEXT,
        name TEXT NOT NULL,
        crop TEXT,
        size REAL,
        status TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_farms_org ON farms(org_id);
    CREATE INDEX IF NOT EXISTS idx_farms_farmer ON farms(farmer_id);

    -- Field Activities (Offline-Syncable)
    CREATE TABLE IF NOT EXISTS field_activities (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        farm_id TEXT,
        farmer_id TEXT,
        activity_type TEXT NOT NULL,
        activity_date TEXT NOT NULL,
        client_mutation_id TEXT UNIQUE,
        author_user_id TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_activities_org ON field_activities(org_id);
    CREATE INDEX IF NOT EXISTS idx_activities_farm ON field_activities(farm_id);
    CREATE INDEX IF NOT EXISTS idx_activities_mutation ON field_activities(client_mutation_id);

    -- Expenses
    CREATE TABLE IF NOT EXISTS expenses (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        farm_id TEXT,
        category TEXT,
        expense_date TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_expenses_org ON expenses(org_id);
    CREATE INDEX IF NOT EXISTS idx_expenses_farm ON expenses(farm_id);

    -- Diagnostic Scans
    CREATE TABLE IF NOT EXISTS scans (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        farm_id TEXT,
        crop TEXT,
        disease TEXT,
        scan_date TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_scans_org ON scans(org_id);
    CREATE INDEX IF NOT EXISTS idx_scans_farm ON scans(farm_id);

    -- Commodities (MarketLens)
    CREATE TABLE IF NOT EXISTS commodities (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        code TEXT,
        name TEXT NOT NULL,
        category TEXT,
        unit TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_commodities_org ON commodities(org_id);

    -- Market Prices (MarketLens)
    CREATE TABLE IF NOT EXISTS market_prices (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        commodity_id TEXT NOT NULL,
        market_name TEXT,
        price_type TEXT,
        price_date TEXT NOT NULL,
        status TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_prices_org ON market_prices(org_id);
    CREATE INDEX IF NOT EXISTS idx_prices_comm ON market_prices(commodity_id);
    CREATE INDEX IF NOT EXISTS idx_prices_date ON market_prices(price_date);

    -- Market Research (MarketLens)
    CREATE TABLE IF NOT EXISTS market_research (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        title TEXT NOT NULL,
        research_date TEXT,
        commodity_id TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_research_org ON market_research(org_id);

    -- Impact Projects (ImpactOS)
    CREATE TABLE IF NOT EXISTS impact_projects (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        code TEXT,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        is_archived INTEGER NOT NULL DEFAULT 0,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_projects_org ON impact_projects(org_id);

    -- Impact Beneficiaries (ImpactOS)
    CREATE TABLE IF NOT EXISTS impact_beneficiaries (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        project_id TEXT,
        beneficiary_code TEXT,
        national_id TEXT,
        status TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_beneficiaries_org ON impact_beneficiaries(org_id);
    CREATE INDEX IF NOT EXISTS idx_beneficiaries_proj ON impact_beneficiaries(project_id);

    -- Impact Indicators (ImpactOS)
    CREATE TABLE IF NOT EXISTS impact_indicators (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        project_id TEXT,
        code TEXT,
        category TEXT,
        status TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_indicators_org ON impact_indicators(org_id);
    CREATE INDEX IF NOT EXISTS idx_indicators_proj ON impact_indicators(project_id);

    -- Impact Progress Records (ImpactOS)
    CREATE TABLE IF NOT EXISTS impact_progress_records (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        indicator_id TEXT NOT NULL,
        reporting_period TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_progress_org ON impact_progress_records(org_id);
    CREATE INDEX IF NOT EXISTS idx_progress_ind ON impact_progress_records(indicator_id);

    -- Impact Activities (ImpactOS)
    CREATE TABLE IF NOT EXISTS impact_activities (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        project_id TEXT,
        activity_type TEXT,
        activity_date TEXT,
        status TEXT NOT NULL,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_impact_act_org ON impact_activities(org_id);
    CREATE INDEX IF NOT EXISTS idx_impact_act_proj ON impact_activities(project_id);

    -- Impact Reports (ImpactOS)
    CREATE TABLE IF NOT EXISTS impact_reports (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL,
        report_type TEXT,
        data TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_reports_org ON impact_reports(org_id);
    """)

    conn.commit()
    conn.close()
    logger.info("AgroTrack SQLite database schema initialized successfully.")


# ── Generic Record Operations ────────────────────────────────────────────────

def save_record(table: str, doc: Dict[str, Any], org_id: Optional[str] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Inserts or updates a document record in the specified table.
    Ensures org_id consistency and persists full JSON representation.
    """
    record_id = doc.get("id") or doc.get("reportId") or doc.get("clientMutationId")
    if not record_id:
        raise ValueError(f"Document missing 'id' field for table {table}")
    doc["id"] = record_id

    effective_org = org_id or doc.get("orgId") or "org_greenvalley_01"
    doc["orgId"] = effective_org

    now_iso = doc.get("createdAt") or doc.get("clientCreatedAt") or datetime.utcnow().isoformat() + "Z"
    if "createdAt" not in doc:
        doc["createdAt"] = now_iso

    json_str = json.dumps(doc, ensure_ascii=False)

    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # Extract indexed columns based on table
    if table == "organisations":
        cur.execute("""
            INSERT INTO organisations (id, name, code, tier, country, currency, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, code=excluded.code, tier=excluded.tier,
                country=excluded.country, currency=excluded.currency,
                data=excluded.data;
        """, (record_id, doc.get("name", ""), doc.get("code", ""), doc.get("tier", "standard"),
              doc.get("country", "Kenya"), doc.get("currency", "KES"), json_str, now_iso))

    elif table == "organisation_members":
        cur.execute("""
            INSERT INTO organisation_members (id, org_id, user_id, email, role, status, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                role=excluded.role, status=excluded.status, data=excluded.data;
        """, (record_id, effective_org, doc.get("userId", ""), doc.get("email", ""),
              str(doc.get("role", "")), doc.get("status", "active"), json_str, now_iso))

    elif table == "farmers":
        cur.execute("""
            INSERT INTO farmers (id, org_id, farmer_code, national_id, first_name, last_name, phone, status, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                farmer_code=excluded.farmer_code, national_id=excluded.national_id,
                first_name=excluded.first_name, last_name=excluded.last_name,
                phone=excluded.phone, status=excluded.status, data=excluded.data;
        """, (record_id, effective_org, doc.get("farmerCode", ""), doc.get("nationalId", ""),
              doc.get("firstName", ""), doc.get("lastName", ""), doc.get("phone", ""),
              doc.get("status", "active"), json_str, now_iso))

    elif table == "farms":
        cur.execute("""
            INSERT INTO farms (id, org_id, farmer_id, name, crop, size, status, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                farmer_id=excluded.farmer_id, name=excluded.name, crop=excluded.crop,
                size=excluded.size, status=excluded.status, data=excluded.data;
        """, (record_id, effective_org, doc.get("farmerId", ""), doc.get("name", ""),
              doc.get("crop", ""), float(doc.get("size", 1.0) or 1.0),
              doc.get("status", "active"), json_str, now_iso))

    elif table == "field_activities":
        cur.execute("""
            INSERT INTO field_activities (id, org_id, farm_id, farmer_id, activity_type, activity_date, client_mutation_id, author_user_id, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                activity_type=excluded.activity_type,
                activity_date=excluded.activity_date,
                author_user_id=excluded.author_user_id,
                data=excluded.data;
        """, (record_id, effective_org, doc.get("farmId", ""), doc.get("farmerId", ""),
              doc.get("activityType", "farm_visit"), doc.get("activityDate", ""),
              doc.get("clientMutationId"), doc.get("authorUserId") or doc.get("recordedByUserId"),
              json_str, now_iso))

    elif table == "expenses":
        cur.execute("""
            INSERT INTO expenses (id, org_id, farm_id, category, expense_date, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                farm_id=excluded.farm_id, category=excluded.category,
                expense_date=excluded.expense_date, data=excluded.data;
        """, (record_id, effective_org, doc.get("farmId", ""), doc.get("category", ""),
              doc.get("date", ""), json_str, now_iso))

    elif table == "scans":
        cur.execute("""
            INSERT INTO scans (id, org_id, farm_id, crop, disease, scan_date, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                crop=excluded.crop, disease=excluded.disease, data=excluded.data;
        """, (record_id, effective_org, doc.get("farmId", ""), doc.get("crop", ""),
              doc.get("disease", ""), doc.get("date") or doc.get("time", ""), json_str, now_iso))

    elif table == "commodities":
        cur.execute("""
            INSERT INTO commodities (id, org_id, code, name, category, unit, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, category=excluded.category, unit=excluded.unit, data=excluded.data;
        """, (record_id, effective_org, doc.get("code", ""), doc.get("name", ""),
              str(doc.get("category", "")), doc.get("unit", "kg"), json_str, now_iso))

    elif table == "market_prices":
        cur.execute("""
            INSERT INTO market_prices (id, org_id, commodity_id, market_name, price_type, price_date, status, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                market_name=excluded.market_name, price_type=excluded.price_type,
                price_date=excluded.price_date, status=excluded.status, data=excluded.data;
        """, (record_id, effective_org, doc.get("commodityId", ""), doc.get("marketName", ""),
              str(doc.get("priceType", "")), doc.get("dateCollected", ""),
              str(doc.get("verificationStatus", "unverified")), json_str, now_iso))

    elif table == "market_research":
        cur.execute("""
            INSERT INTO market_research (id, org_id, title, research_date, commodity_id, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title, research_date=excluded.research_date, data=excluded.data;
        """, (record_id, effective_org, doc.get("title", ""), doc.get("date", ""),
              doc.get("commodityId", ""), json_str, now_iso))

    elif table == "impact_projects":
        is_arch = 1 if doc.get("isArchived") else 0
        cur.execute("""
            INSERT INTO impact_projects (id, org_id, code, name, status, is_archived, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, status=excluded.status, is_archived=excluded.is_archived, data=excluded.data;
        """, (record_id, effective_org, doc.get("code", ""), doc.get("name", ""),
              str(doc.get("status", "active")), is_arch, json_str, now_iso))

    elif table == "impact_beneficiaries":
        cur.execute("""
            INSERT INTO impact_beneficiaries (id, org_id, project_id, beneficiary_code, national_id, status, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                project_id=excluded.project_id, status=excluded.status, data=excluded.data;
        """, (record_id, effective_org, doc.get("projectId", ""), doc.get("beneficiaryCode", ""),
              doc.get("nationalId", ""), str(doc.get("status", "active")), json_str, now_iso))

    elif table == "impact_indicators":
        cur.execute("""
            INSERT INTO impact_indicators (id, org_id, project_id, code, category, status, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status, data=excluded.data;
        """, (record_id, effective_org, doc.get("projectId", ""), doc.get("code", ""),
              str(doc.get("category", "")), str(doc.get("status", "on_track")), json_str, now_iso))

    elif table == "impact_progress_records":
        cur.execute("""
            INSERT INTO impact_progress_records (id, org_id, indicator_id, reporting_period, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                reporting_period=excluded.reporting_period, data=excluded.data;
        """, (record_id, effective_org, doc.get("indicatorId", ""), doc.get("reportingPeriod", ""), json_str, now_iso))

    elif table == "impact_activities":
        cur.execute("""
            INSERT INTO impact_activities (id, org_id, project_id, activity_type, activity_date, status, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                activity_type=excluded.activity_type, status=excluded.status, data=excluded.data;
        """, (record_id, effective_org, doc.get("projectId", ""), str(doc.get("activityType", "")),
              doc.get("date", ""), str(doc.get("status", "completed")), json_str, now_iso))

    elif table == "impact_reports":
        cur.execute("""
            INSERT INTO impact_reports (id, org_id, report_type, data, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                report_type=excluded.report_type, data=excluded.data;
        """, (record_id, effective_org, doc.get("reportType", "standard"), json_str, now_iso))

    else:
        raise ValueError(f"Unknown database table: {table}")

    conn.commit()
    conn.close()
    return doc


def get_record(table: str, record_id: str, org_id: Optional[str] = None, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves a single record by id, optionally enforcing organisation isolation."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    if org_id and table != "organisations":
        cur.execute(f"SELECT data FROM {table} WHERE id = ? AND org_id = ?", (record_id, org_id))
    else:
        cur.execute(f"SELECT data FROM {table} WHERE id = ?", (record_id,))

    row = cur.fetchone()
    conn.close()

    if row:
        return json.loads(row["data"])
    return None


def list_records(
    table: str,
    org_id: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    sort_key: Optional[str] = None,
    reverse: bool = False,
    limit: Optional[int] = None,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Lists records from table scoped to org_id with optional in-memory filter and sorting.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    params = []
    where_clauses = []

    if org_id:
        where_clauses.append("org_id = ?")
        params.append(org_id)

    query = f"SELECT data FROM {table}"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY created_at DESC"
    if limit and not filters and not sort_key:
        query += f" LIMIT {int(limit)}"

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    results = [json.loads(r["data"]) for r in rows]

    # Apply application-level filters if provided
    if filters:
        filtered = []
        for doc in results:
            match = True
            for k, v in filters.items():
                if v is None:
                    continue
                doc_val = doc.get(k)
                if isinstance(v, list):
                    if doc_val not in v:
                        match = False
                        break
                elif doc_val != v:
                    match = False
                    break
            if match:
                filtered.append(doc)
        results = filtered

    if sort_key:
        results.sort(key=lambda x: str(x.get(sort_key) or ""), reverse=reverse)

    if limit and len(results) > limit:
        results = results[:limit]

    return results


def delete_record(table: str, record_id: str, org_id: Optional[str] = None, db_path: str = DB_PATH) -> bool:
    """Deletes a record by id, optionally scoped to organisation."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    if org_id and table != "organisations":
        cur.execute(f"DELETE FROM {table} WHERE id = ? AND org_id = ?", (record_id, org_id))
    else:
        cur.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))

    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def count_records(table: str, org_id: Optional[str] = None, db_path: str = DB_PATH) -> int:
    """Counts records in table, optionally scoped to organisation."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    if org_id:
        cur.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE org_id = ?", (org_id,))
    else:
        cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")

    row = cur.fetchone()
    count = row["cnt"] if row else 0
    conn.close()
    return count


class _DbTenantListProxy(list):
    """A list proxy that immediately persists appended items to the SQLite table."""
    def __init__(self, table: str, org_id: str, items: List[Dict[str, Any]], db_path: str = DB_PATH):
        super().__init__(items)
        self.table = table
        self.org_id = org_id
        self.db_path = db_path

    def append(self, item: Dict[str, Any]):
        super().append(item)
        if isinstance(item, dict):
            save_record(self.table, item, org_id=self.org_id, db_path=self.db_path)

    def extend(self, items: List[Dict[str, Any]]):
        for item in items:
            self.append(item)


class DbTenantCollection:
    """
    A persistent, dictionary-like collection over a SQLite table partitioned by org_id.
    Every read queries SQLite in WAL mode; every write persists immediately to disk.
    Guarantees ACID transactions and persistence across server restarts and multiple workers.
    """
    def __init__(self, table: str, db_path: str = DB_PATH):
        self.table = table
        self.db_path = db_path

    def get(self, org_id: str, default=None) -> List[Dict[str, Any]]:
        recs = list_records(self.table, org_id=org_id, db_path=self.db_path)
        if not recs and default is not None:
            return default
        return _DbTenantListProxy(self.table, org_id, recs, db_path=self.db_path)

    def __getitem__(self, org_id: str) -> List[Dict[str, Any]]:
        recs = list_records(self.table, org_id=org_id, db_path=self.db_path)
        return _DbTenantListProxy(self.table, org_id, recs, db_path=self.db_path)

    def __setitem__(self, org_id: str, items: List[Dict[str, Any]]):
        current_ids = {item["id"] for item in items if isinstance(item, dict) and "id" in item}
        existing = list_records(self.table, org_id=org_id, db_path=self.db_path)
        for ex in existing:
            if ex.get("id") not in current_ids:
                delete_record(self.table, ex["id"], org_id=org_id, db_path=self.db_path)
        for item in items:
            if isinstance(item, dict):
                save_record(self.table, item, org_id=org_id, db_path=self.db_path)

    def __contains__(self, org_id: str) -> bool:
        return count_records(self.table, org_id=org_id, db_path=self.db_path) > 0

    def items(self):
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(f"SELECT DISTINCT org_id FROM {self.table}")
        orgs = [r[0] for r in cur.fetchall()]
        conn.close()
        return [(o, _DbTenantListProxy(self.table, o, list_records(self.table, org_id=o, db_path=self.db_path), db_path=self.db_path)) for o in orgs]

    def keys(self):
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute(f"SELECT DISTINCT org_id FROM {self.table}")
        orgs = [r[0] for r in cur.fetchall()]
        conn.close()
        return orgs

    def values(self):
        return [self[o] for o in self.keys()]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())


def seed_default_data(db_path: str = DB_PATH):
    """
    Seeds initial default data into SQLite tables if the database is newly initialized.
    Will never overwrite existing user data on restart.
    """
    init_db(db_path)

    # Check if organisations table is empty
    if count_records("organisations", db_path=db_path) > 0:
        logger.info("Database already populated. Skipping seed initialization.")
        return

    logger.info("Database empty. Seeding initial baseline datasets...")

    # Seed Default Organisation
    default_org = {
        "id": "org_greenvalley_01",
        "name": "GreenValley AgTech Cooperative",
        "code": "GV-AGTECH",
        "tier": "enterprise",
        "country": "Kenya",
        "currency": "KES",
        "createdAt": "2026-01-15T08:00:00Z"
    }
    save_record("organisations", default_org, org_id=default_org["id"], db_path=db_path)

    second_org = {
        "id": "org_highland_02",
        "name": "Highland Smallholders Initiative",
        "code": "HL-AGRI",
        "tier": "standard",
        "country": "Kenya",
        "currency": "KES",
        "createdAt": "2026-02-01T09:00:00Z"
    }
    save_record("organisations", second_org, org_id=second_org["id"], db_path=db_path)

    # Seed Organisation Members
    default_members = [
        {"id": "mem_001", "userId": "usr_admin_001", "name": "Sarah Mwangi", "email": "sarah.mwangi@agrotrack.ai", "role": "Organisation Administrator", "status": "active", "joinedAt": "2026-01-15T08:00:00Z"},
        {"id": "mem_002", "userId": "usr_mgr_002", "name": "David Kiprop", "email": "david.kiprop@agrotrack.ai", "role": "Project Manager", "status": "active", "joinedAt": "2026-02-01T09:30:00Z"},
        {"id": "mem_003", "userId": "usr_field_003", "name": "Amina Otieno", "email": "amina.otieno@agrotrack.ai", "role": "Field Officer", "status": "active", "joinedAt": "2026-02-15T10:00:00Z"},
        {"id": "mem_004", "userId": "usr_analyst_004", "name": "Brian Njoroge", "email": "brian.njoroge@agrotrack.ai", "role": "Analyst", "status": "active", "joinedAt": "2026-03-01T11:15:00Z"},
        {"id": "mem_005", "userId": "usr_viewer_005", "name": "Grace Wanjiku", "email": "grace.wanjiku@agrotrack.ai", "role": "Viewer", "status": "active", "joinedAt": "2026-03-10T14:00:00Z"},
    ]
    for m in default_members:
        save_record("organisation_members", m, org_id="org_greenvalley_01", db_path=db_path)

    # Import seed dictionaries from domain modules
    try:
        from backend.agrotrack.seed_data import (
            DEFAULT_FARMERS,
            DEFAULT_FARMS,
            DEFAULT_ACTIVITIES,
            DEFAULT_EXPENSES,
            DEFAULT_SCANS,
        )
        for org_id, farmers in DEFAULT_FARMERS.items():
            for f in farmers:
                save_record("farmers", f, org_id=org_id, db_path=db_path)

        for org_id, farms in DEFAULT_FARMS.items():
            for fm in farms:
                save_record("farms", fm, org_id=org_id, db_path=db_path)

        for org_id, acts in DEFAULT_ACTIVITIES.items():
            for a in acts:
                save_record("field_activities", a, org_id=org_id, db_path=db_path)

        for org_id, exps in DEFAULT_EXPENSES.items():
            for e in exps:
                save_record("expenses", e, org_id=org_id, db_path=db_path)

        for org_id, scns in DEFAULT_SCANS.items():
            for s in scns:
                save_record("scans", s, org_id=org_id, db_path=db_path)
    except Exception as e:
        logger.warning(f"AgroTrack domain seed notice: {e}")

    try:
        from backend.marketlens.seed_data import (
            DEFAULT_COMMODITIES,
            DEFAULT_PRICES,
            DEFAULT_RESEARCH,
        )
        for org_id, comms in DEFAULT_COMMODITIES.items():
            for c in comms:
                save_record("commodities", c, org_id=org_id, db_path=db_path)

        for org_id, prices in DEFAULT_PRICES.items():
            for p in prices:
                save_record("market_prices", p, org_id=org_id, db_path=db_path)

        for org_id, res in DEFAULT_RESEARCH.items():
            for r in res:
                save_record("market_research", r, org_id=org_id, db_path=db_path)
    except Exception as e:
        logger.warning(f"MarketLens domain seed notice: {e}")

    try:
        from backend.impactos.seed_data import (
            DEFAULT_PROJECTS,
            DEFAULT_BENEFICIARIES,
            DEFAULT_INDICATORS,
            DEFAULT_PROGRESS,
            DEFAULT_IMPACT_ACTIVITIES,
            DEFAULT_REPORTS,
        )
        for org_id, projs in DEFAULT_PROJECTS.items():
            for pj in projs:
                save_record("impact_projects", pj, org_id=org_id, db_path=db_path)

        for org_id, bens in DEFAULT_BENEFICIARIES.items():
            for b in bens:
                save_record("impact_beneficiaries", b, org_id=org_id, db_path=db_path)

        for org_id, inds in DEFAULT_INDICATORS.items():
            for ind in inds:
                save_record("impact_indicators", ind, org_id=org_id, db_path=db_path)

        for org_id, prgs in DEFAULT_PROGRESS.items():
            for pr in prgs:
                save_record("impact_progress_records", pr, org_id=org_id, db_path=db_path)

        for org_id, acts in DEFAULT_IMPACT_ACTIVITIES.items():
            for a in acts:
                save_record("impact_activities", a, org_id=org_id, db_path=db_path)

        for org_id, reps in DEFAULT_REPORTS.items():
            for r in reps:
                save_record("impact_reports", r, org_id=org_id, db_path=db_path)
    except Exception as e:
        logger.warning(f"ImpactOS domain seed notice: {e}")

    logger.info("Database seeding complete.")

def reset_db(db_path: str = DB_PATH):
    """
    Completely drops all tables and re-initializes and re-seeds baseline data.
    Ensures a pristine state for test isolation and clean resets.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    tables = [
        "organisations", "organisation_members", "farmers", "farms",
        "field_activities", "expenses", "scans", "commodities",
        "market_prices", "market_research", "impact_projects",
        "impact_beneficiaries", "impact_indicators",
        "impact_progress_records", "impact_activities", "impact_reports"
    ]
    for tbl in tables:
        cur.execute(f"DROP TABLE IF EXISTS {tbl};")
    conn.commit()
    conn.close()
    init_db(db_path)
    seed_default_data(db_path)
