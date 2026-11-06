-- Run after attaching github (see README.md). One bounded API scan, outside the inventory join.
-- Inventory is fictional. Different tags are review candidates, not guaranteed safe upgrades.
WITH fetched AS MATERIALIZED (
    SELECT * FROM github.main.releases('duckdb', 'duckdb')
), latest AS (
    SELECT tag_name, html_url
    FROM fetched
    WHERE prerelease = false AND published_at IS NOT NULL
    ORDER BY CAST(published_at AS TIMESTAMPTZ) DESC
    LIMIT 1
)
SELECT inventory.project,
       inventory.installed_tag,
       latest.tag_name AS published_tag,
       latest.html_url AS release_url
FROM read_csv('inventory.csv', header = true, all_varchar = true) AS inventory
CROSS JOIN latest
WHERE inventory.owner = 'duckdb'
  AND inventory.repo = 'duckdb'
  AND inventory.installed_tag <> latest.tag_name
ORDER BY inventory.project;
