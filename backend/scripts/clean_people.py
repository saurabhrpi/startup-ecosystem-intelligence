"""
Clean existing Person data in Neo4j using a generalized name validator.

Usage examples:
  - Dry run founders only (default):
      python backend/scripts/clean_people.py
  - Mark invalid founders with label :InvalidPerson:
      python backend/scripts/clean_people.py --action mark-invalid --yes
  - Delete invalid founders (irreversible):
      python backend/scripts/clean_people.py --action delete-invalid --yes
  - Process all Person nodes (not just founders):
      python backend/scripts/clean_people.py --all-people --action mark-invalid --yes

Env required for Neo4j:
  NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

Optional env for ambiguous cases via LLM:
  USE_LLM_NAME_GUARD=true, OPENAI_API_KEY
"""

import argparse
from typing import Dict, List, Tuple

from backend.utils.neo4j_store import Neo4jStore
from backend.utils.name_guard import is_probable_person_name


def fetch_people(store: Neo4jStore, founders_only: bool, limit: int | None) -> List[Dict[str, str]]:
    query = (
        """
        MATCH (p:Person)-[:FOUNDED]->(c:Company)
        RETURN p.id AS id, p.name AS name, coalesce(p.role,'') AS role
        """
        if founders_only
        else """
        MATCH (p:Person)
        RETURN p.id AS id, p.name AS name, coalesce(p.role,'') AS role
        """
    )
    if limit and limit > 0:
        query += "\nLIMIT $limit"
    with store.driver.session() as session:
        rows = session.run(query, {"limit": limit} if limit else {})
        return [
            {"id": row.get("id"), "name": row.get("name") or "", "role": row.get("role") or ""}
            for row in rows
        ]


def classify_people(people: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    valid: List[Dict[str, str]] = []
    invalid: List[Dict[str, str]] = []
    for p in people:
        name = (p.get("name") or "").strip()
        if is_probable_person_name(name):
            valid.append(p)
        else:
            invalid.append(p)
    return valid, invalid


def mark_invalid(store: Neo4jStore, ids: List[str]) -> int:
    if not ids:
        return 0
    with store.driver.session() as session:
        res = session.run(
            """
            UNWIND $ids AS pid
            MATCH (p:Person {id: pid})
            SET p:InvalidPerson
            RETURN count(p) AS cnt
            """,
            {"ids": ids},
        )
        return res.single().get("cnt", 0)


def delete_invalid(store: Neo4jStore, ids: List[str]) -> int:
    if not ids:
        return 0
    with store.driver.session() as session:
        res = session.run(
            """
            UNWIND $ids AS pid
            MATCH (p:Person {id: pid})
            DETACH DELETE p
            RETURN count(pid) AS deleted
            """,
            {"ids": ids},
        )
        return res.single().get("deleted", 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean Person nodes using a generalized name validator")
    parser.add_argument("--all-people", action="store_true", help="Process all Person nodes (not just founders)")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for testing")
    parser.add_argument(
        "--action",
        choices=["dry-run", "mark-invalid", "delete-invalid"],
        default="dry-run",
        help="What to do with invalid entries",
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation for destructive actions")
    args = parser.parse_args()

    store = Neo4jStore()
    people = fetch_people(store, founders_only=not args.all_people, limit=args.limit if args.limit > 0 else None)
    valid, invalid = classify_people(people)

    print(f"Total checked: {len(people)} | Valid: {len(valid)} | Invalid: {len(invalid)}")
    if args.action == "dry-run" or not invalid:
        return

    if not args.yes:
        print("Use --yes to apply changes.")
        return

    invalid_ids = [p["id"] for p in invalid if p.get("id")]
    if args.action == "mark-invalid":
        updated = mark_invalid(store, invalid_ids)
        print(f"Marked {updated} people as :InvalidPerson")
    elif args.action == "delete-invalid":
        deleted = delete_invalid(store, invalid_ids)
        print(f"Deleted {deleted} invalid people")


if __name__ == "__main__":
    main()


