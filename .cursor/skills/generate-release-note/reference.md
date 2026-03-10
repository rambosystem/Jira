# Generate Release Note — Reference

## Module → Product Name (Release Note title)

| Jira / 迭代总结 module     | Release Note product name |
|----------------------------|----------------------------|
| Budget Scheduler           | Budget Manager             |
| Dayparting Scheduler       | Dayparting Scheduler       |
| My Report                  | My Report                  |
| SOV                        | SOV                        |
| Calendar Center            | Calendar Center            |
| Creative Management        | Creative Hub               |
| Automation Priority        | Automation / Priority      |

Use the right column as the `#### <Product Name>` heading. Add or change rows per project convention.

## Platform keywords (from summary)

Use these to assign "For <Platform>:" and to detect "All Platforms":

- **Amazon**, **Walmart**, **Target**, **Reddit**, **Kroger**, **Doordash**, **Criteo**, **TikTok**, **Bol**, **Benelux**, **MX** (Walmart MX), **EU**
- **All Platforms**, 全平台 → "For All Platforms:"
- If multiple platforms in one story (e.g. "Criteo & Target & Doordash & Kroger"), either list under "For All Platforms:" or split by platform if the note is clearer that way.

## New vs Update (short)

- **New**: Rollout to X, first-time support, 接入, 支持 &lt;platform&gt; (new), New Version Support (new platform).
- **Update**: 优化, 修复, Allow/Add/Update &lt;feature&gt;, 交互优化, 补偿, 埋点, 重命名.

## Output file naming

- `Release-Note-Sprint<N>-V<version>.md` (e.g. `Release-Note-Sprint4-V3.29.md`)
- or `Release-Note-<sprint_name>.md` when version is not set.

## Details link

- Prefer user-provided Confluence/wiki URL.
- Placeholder: `https://pacvue-enterprise.atlassian.net/wiki/x/zIJMSg` (replace with real link when available).
