import json
import sys
from pathlib import Path

proj_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(proj_root))

from src.tools.storage import SessionStorage


def main() -> int:
    json_path = proj_root / "data" / "chat_sessions.json"
    if not json_path.exists():
        print(f"未找到 {json_path}, 无需迁移。")
        return 0

    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("读取 JSON 失败:", exc)
        return 2

    if not isinstance(raw, dict):
        print("JSON 格式不为对象，取消迁移。")
        return 3

    db_path = json_path.with_suffix('.db')
    storage = SessionStorage(str(db_path))
    storage.init_db()

    count = 0
    for session_key, messages in raw.items():
        if not isinstance(session_key, str) or not isinstance(messages, list):
            continue
        try:
            storage.save_session(session_key, messages)
            count += 1
        except Exception as exc:
            print(f"保存会话 {session_key} 失败: {exc}")

    print(f"迁移完成，写入 {count} 个会话到 {db_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
