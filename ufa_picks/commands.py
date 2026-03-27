# -*- coding: utf-8 -*-
"""Click commands."""
import os
from glob import glob
from subprocess import call

import click

HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.join(HERE, os.pardir)
TEST_PATH = os.path.join(PROJECT_ROOT, "tests")


@click.command()
@click.option(
    "-c/-C",
    "--coverage/--no-coverage",
    default=True,
    is_flag=True,
    help="Show coverage report",
)
@click.option(
    "-k",
    "--filter",
    default=None,
    help="Filter tests by keyword expressions",
)
def test(coverage, filter):
    """Run the tests."""
    import pytest

    args = [TEST_PATH, "--verbose"]
    if coverage:
        args.append("--cov=ufa_picks")
    if filter:
        args.extend(["-k", filter])
    rv = pytest.main(args=args)
    exit(rv)


@click.command()
@click.option(
    "-f",
    "--fix-imports",
    default=True,
    is_flag=True,
    help="Fix imports using isort, before linting",
)
@click.option(
    "-c",
    "--check",
    default=False,
    is_flag=True,
    help="Don't make any changes to files, just confirm they are formatted correctly",
)
def lint(fix_imports, check):
    """Lint and check code style with black, flake8 and isort."""
    skip = ["node_modules", "requirements", "migrations"]
    root_files = glob("*.py")
    root_directories = [
        name for name in next(os.walk("."))[1] if not name.startswith(".")
    ]
    files_and_directories = [
        arg for arg in root_files + root_directories if arg not in skip
    ]

    def execute_tool(description, *args):
        """Execute a checking tool with its arguments."""
        command_line = list(args) + files_and_directories
        click.echo(f"{description}: {' '.join(command_line)}")
        rv = call(command_line)
        if rv != 0:
            exit(rv)

    isort_args = []
    black_args = []
    if check:
        isort_args.append("--check")
        black_args.append("--check")
    if fix_imports:
        execute_tool("Fixing import order", "isort", *isort_args)
    execute_tool("Formatting style", "black", *black_args)
    execute_tool("Checking code style", "flake8")

@click.command()
@click.option("--table", "-t", multiple=True, help="Specific table to sync")
@click.option("--all-tables", "-a", is_flag=True, help="Sync all tables")
def sync_db(table, all_tables):
    """Sync dev database from production database (read-only prod.env needed)."""
    import os
    from environs import Env
    from sqlalchemy import create_engine, MetaData, text
    from ufa_picks.extensions import db, bcrypt

    env = Env()
    prod_env_path = os.path.join(PROJECT_ROOT, "prod.env")
    if not os.path.exists(prod_env_path):
        click.echo("Error: prod.env file not found at project root.")
        return
    
    # Read prod.env manually to avoid environment variable shadowing from the container
    prod_db_url = None
    with open(prod_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                prod_db_url = line.split("=", 1)[1].strip().strip("'").strip('"')
                break

    if not prod_db_url:
        click.echo("Error: DATABASE_URL not found in prod.env")
        return

    # Safety check: Don't sync if URLs are identical
    dev_db_url = str(db.engine.url)
    if prod_db_url == dev_db_url:
        click.echo("Error: Production URL is the same as Development URL.")
        click.echo(f"URL: {prod_db_url}")
        click.echo("Aborting to prevent self-syncing.")
        return

    click.echo(f"Syncing from: {prod_db_url.split('@')[-1] if '@' in prod_db_url else 'specified prod source'}")
    prod_engine = create_engine(prod_db_url)
    prod_metadata = MetaData()
    prod_metadata.reflect(bind=prod_engine)

    if all_tables:
        tables_to_sync = prod_metadata.sorted_tables
    else:
        sync_names = set(table)
        added = True
        while added:
            added = False
            for t in prod_metadata.sorted_tables:
                if t.name not in sync_names:
                    for fk in t.foreign_keys:
                        if fk.column.table.name in sync_names:
                            sync_names.add(t.name)
                            added = True

        tables_to_sync = [t for t in prod_metadata.sorted_tables if t.name in sync_names]
        if not tables_to_sync:
            click.echo("No valid tables specified.")
            return

    # Filter out alembic_version as it should never be synced between environments
    tables_to_sync = [t for t in tables_to_sync if t.name != "alembic_version"]

    qa_password_hash = bcrypt.generate_password_hash("swordf1sh!")

    # 1. Determine all local tables that need to be cleared to avoid constraint violations
    local_metadata = db.metadata
    local_tables_by_name = {t.name: t for t in local_metadata.sorted_tables}
    
    # We want to clear any table that we are about to sync, plus its local dependents
    tables_to_clear = []
    sync_names_set = {t.name for t in tables_to_sync}
    
    # Iterate through local tables in reverse topological order
    for t in reversed(local_metadata.sorted_tables):
        if t.name in sync_names_set:
            tables_to_clear.append(t)
        else:
            # If a local table depends on something we are syncing, we MUST clear it too
            for fk in t.foreign_keys:
                if fk.column.table.name in sync_names_set:
                    tables_to_clear.append(t)
                    break

    for t in tables_to_clear:
        try:
            click.echo(f"Clearing table: {t.name} locally...")
            db.session.execute(text(f"DELETE FROM {t.name}"))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            click.echo(f"  -> Warning: Could not clear table {t.name} locally: {e}")

    # 2. Pull and Insert in topological order
    with prod_engine.connect() as prod_conn:
        for t in tables_to_sync:
            # Ensure the table exists in dev before trying to insert into it
            try:
                t.create(bind=db.engine, checkfirst=True)
            except Exception:
                pass

            click.echo(f"Syncing table from prod: {t.name}...")
            
            prod_table = prod_metadata.tables.get(t.name)
            if prod_table is None:
                click.echo(f"  -> Table {t.name} not found in production DB.")
                continue

            results = []
            try:
                results = prod_conn.execute(prod_table.select()).fetchall()
            except Exception as e:
                click.echo(f"  -> Warning: Could not pull table {t.name} from prod: {e}")
                try:
                    prod_conn.rollback()
                except Exception:
                    pass
                continue

            if results:
                try:
                    # Get the local table object if it exists to ensure correct metadata mapping
                    local_table = db.metadata.tables.get(t.name)
                    if local_table is None:
                        # Fallback to the production table object but strip its bind
                        local_table = prod_table

                    insert_data = []
                    for row in results:
                        row_dict = dict(row._mapping)
                        if t.name == "users" and "password" in row_dict:
                            row_dict["password"] = qa_password_hash
                        insert_data.append(row_dict)
                    
                    chunk_size = 500
                    for i in range(0, len(insert_data), chunk_size):
                        db.session.execute(local_table.insert(), insert_data[i:i+chunk_size])
                    
                    db.session.commit()
                    click.echo(f"  -> Loaded {len(results)} rows into {t.name}.")
                except Exception as e:
                    db.session.rollback()
                    click.echo(f"  -> Warning: Could not insert rows into {t.name} locally: {e}")
            else:
                click.echo(f"  -> No data found in prod for {t.name}.")
    
    db.session.commit()
    click.echo("Database sync complete.")
