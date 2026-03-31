from __future__ import annotations

from job_search_lib import DASHBOARD_OVERVIEW, refresh_dashboard_data


def main() -> None:
    refresh_dashboard_data()
    print(f"Dashboard data refreshed at {DASHBOARD_OVERVIEW}")


if __name__ == "__main__":
    main()
