"""Append email to PLATFORM_ADMIN_EMAILS in .env (idempotent)."""

from pathlib import Path

TARGET = "christambapro@gmail.com"
ENV = Path(__file__).resolve().parents[2] / ".env"


def main() -> None:
    text = ENV.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        if line.startswith("PLATFORM_ADMIN_EMAILS="):
            found = True
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            raw = [e.strip() for e in val.replace(";", ",").split(",") if e.strip()]
            if not any(e.lower() == TARGET.lower() for e in raw):
                raw.append(TARGET)
            line = "PLATFORM_ADMIN_EMAILS=" + ",".join(raw)
            print("UPDATED", len(raw))
        out.append(line)
    if not found:
        out.append(f"PLATFORM_ADMIN_EMAILS={TARGET}")
        print("CREATED")
    ENV.write_text("\n".join(out) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    check = ENV.read_text(encoding="utf-8")
    print("contains", TARGET.lower() in check.lower())


if __name__ == "__main__":
    main()
