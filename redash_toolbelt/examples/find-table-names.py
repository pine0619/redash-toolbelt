import itertools, json, re
import click
from redash_toolbelt import Redash


# This regex captures three groups:
#
#   0. A FROM or JOIN statement
#   1. The whitespace character between FROM/JOIN and table name
#   2. The table name
PATTERN = re.compile(r"(?:FROM|JOIN)(?:\s+)([^\s\(\)]+)", flags=re.IGNORECASE|re.UNICODE)


def find_table_names(url, key, data_source_id):

    client = Redash(url, key)

    schema_tables = [
        token.get("name")
        for token in client._get(f"api/data_sources/{data_source_id}/schema")
        .json()
        .get("schema", [])
    ]

    queries = [
        query
        for query in client.paginate(client.queries)
        if query.get("data_source_id", None) == int(data_source_id)
    ]

    tables_by_qry = {
        query["id"]: [
            match
            for match in re.findall(PATTERN, query["query"])
            if match in schema_tables or len(schema_tables) == 0
        ]
        for query in queries
        if re.search(PATTERN, query["query"])
    }

    return tables_by_qry


def print_summary(tables_by_qry):
    """Builds a summary showing table names and count of queries that reference them."""

    summary = {
        table_name: sum(
            [1 for tables in tables_by_qry.values() if table_name in tables]
        )
        for table_name in itertools.chain(*tables_by_qry.values())
    }

    align = max([len(table_name) for table_name in summary.keys()])

    print("\n")
    print(f"{'table':>{align}} | {'number of queries':>17}")
    print("-" * align + " | " + "-" * 17)

    for t, num in sorted(summary.items(), key=lambda item: item[1], reverse=True):
        print(f"{t:>{align}} | {num:>17}")

    print("\n")


def print_details(tables_by_qry):
    """Prints out (query_id, tablename) tuples"""

    details = [
        [(query, table) for table in tables] for query, tables in tables_by_qry.items()
    ]

    for row in itertools.chain(*details):
        print(",".join([str(i) for i in row]))


@click.command()
@click.argument("url",)
@click.argument("key",)
@click.argument("data_source_id")
@click.option("--detail", is_flag=True, help="Prints out all table/query pairs?")
def main(url, key, data_source_id, detail):
    """Find table names referenced in queries against DATA_SOURCE_ID"""

    data = find_table_names(url, key, data_source_id)

    if detail:
        print_details(data)
    else:
        print_summary(data)


if __name__ == "__main__":
    main()
