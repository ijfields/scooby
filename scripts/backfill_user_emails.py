"""Backfill user.email + display_name + avatar_url from Clerk's Backend API.

Run once after deploying the auth fix. Idempotent — re-running skips users
whose email already looks real (not the @clerk.user / user@scooby.app placeholders).

Usage (from a Railway service container with CLERK_SECRET_KEY set):
    python scripts/backfill_user_emails.py             # dry-run
    python scripts/backfill_user_emails.py --apply     # actually write
"""

from __future__ import annotations

import argparse
import os
import sys
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


PLACEHOLDER_SUFFIXES = ("@clerk.user", "@scooby.app")


def looks_like_placeholder(email: str | None) -> bool:
    if not email:
        return True
    return email.endswith(PLACEHOLDER_SUFFIXES)


def fetch_clerk_user(clerk_id: str, secret: str) -> dict | None:
    try:
        resp = httpx.get(
            f"https://api.clerk.com/v1/users/{clerk_id}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as ex:
        print(f"    Clerk API error: {ex}")
        return None


def extract_profile(data: dict) -> dict:
    primary_id = data.get("primary_email_address_id")
    emails = data.get("email_addresses") or []
    email = next(
        (e.get("email_address") for e in emails if e.get("id") == primary_id),
        None,
    ) or (emails[0].get("email_address") if emails else None)

    first = data.get("first_name") or ""
    last = data.get("last_name") or ""
    display_name = f"{first} {last}".strip() or None

    return {
        "email": email,
        "display_name": display_name,
        "avatar_url": data.get("image_url"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="actually write changes (default is dry-run)")
    args = parser.parse_args()

    secret = os.environ.get("CLERK_SECRET_KEY")
    if not secret:
        print("ERROR: CLERK_SECRET_KEY not set in environment")
        return 1

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment")
        return 1

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        users = session.execute(text(
            "SELECT id, clerk_id, email, display_name, avatar_url FROM users "
            "ORDER BY created_at"
        )).fetchall()

        print(f"Found {len(users)} users in DB. "
              f"Mode: {'APPLY' if args.apply else 'DRY RUN'}\n")

        updated = skipped = errored = 0
        for u in users:
            d = dict(u._mapping)
            label = f"{str(d['id'])[:8]} clerk={d['clerk_id']}"

            if not looks_like_placeholder(d["email"]):
                print(f"  {label}: already has real email ({d['email']}) — skip")
                skipped += 1
                continue

            print(f"  {label}: current='{d['email']}' — fetching from Clerk...")
            data = fetch_clerk_user(d["clerk_id"], secret)
            if not data:
                errored += 1
                continue

            profile = extract_profile(data)
            if not profile["email"]:
                print(f"    no email on Clerk record — skip")
                errored += 1
                continue

            print(f"    -> email='{profile['email']}' "
                  f"display_name='{profile['display_name']}' "
                  f"avatar={'yes' if profile['avatar_url'] else 'no'}")

            if args.apply:
                session.execute(
                    text(
                        "UPDATE users SET email = :email, "
                        "display_name = COALESCE(:dn, display_name), "
                        "avatar_url = COALESCE(:av, avatar_url) "
                        "WHERE id = :id"
                    ),
                    {
                        "email": profile["email"],
                        "dn": profile["display_name"],
                        "av": profile["avatar_url"],
                        "id": d["id"],
                    },
                )
                updated += 1

        if args.apply:
            session.commit()

        print(f"\nDone. updated={updated} skipped={skipped} errored={errored}")
        if not args.apply and updated == 0 and errored == 0:
            print("(dry run — re-run with --apply to write)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
