import csv
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def load_dotenv_if_present(base_dir: Path) -> None:
    env_path = base_dir / ".env"
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = (raw_line or "").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = (key or "").strip()
            if not key or key in os.environ:
                continue
            value = (value or "").strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value
    except Exception:
        return


def sanitize_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    out = name
    for ch in invalid:
        out = out.replace(ch, "_")
    return out


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    load_dotenv_if_present(base_dir)

    db_path = Path(os.getenv("DB_PATH", "data/xianyu_data.db"))
    if not db_path.is_absolute():
        db_path = base_dir / db_path
    if not db_path.exists():
        raise SystemExit(f"本地数据库不存在: {db_path}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_root = base_dir / "exports" / f"sqlite_export_{ts}"
    csv_dir = export_root / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            raise SystemExit("未发现可导出的业务表")

        summary: List[Dict] = []
        schema: Dict[str, List[Dict]] = {}

        for table in tables:
            cur.execute(f"PRAGMA table_info({table})")
            cols_info = cur.fetchall()
            columns = [c["name"] for c in cols_info]
            schema[table] = [
                {
                    "name": c["name"],
                    "type": c["type"],
                    "notnull": bool(c["notnull"]),
                    "default": c["dflt_value"],
                    "pk": int(c["pk"]),
                }
                for c in cols_info
            ]

            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()

            csv_path = csv_dir / f"{sanitize_filename(table)}.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([row[col] for col in columns])

            summary.append(
                {
                    "table": table,
                    "rows": len(rows),
                    "file": str(csv_path.relative_to(export_root)).replace("\\", "/"),
                }
            )
            print(f"[OK] {table}: {len(rows)} 行 -> {csv_path.name}")

        (export_root / "schema.json").write_text(
            json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (export_root / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        readme = [
            "SQLite 全量导出说明",
            "",
            f"源数据库: {db_path}",
            f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "目录说明:",
            "- csv/: 每个表一个 CSV 文件（UTF-8 with BOM）",
            "- schema.json: 每张表字段结构",
            "- summary.json: 每张表行数与文件名",
            "",
            "手动导入建议:",
            "1) 先在目标库创建表结构",
            "2) 按 summary.json 顺序导入 CSV",
            "3) 如有关联键，建议先导入基础表（users/cookies 等）",
        ]
        (export_root / "README.txt").write_text("\n".join(readme), encoding="utf-8")

        print(f"\n导出完成: {export_root}")
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
