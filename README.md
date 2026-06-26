# Expedition Story

> 把任一段 iNaturalist 踏查（使用者 × 地點 × 日期區間）自動產成「植被海拔剖面圖」網站。
> Turn any iNaturalist survey (user × place × date-range) into a vegetation elevation-transect site.

荒野保護協會 Society of Wilderness · 通用工具，由二格山稜線剖面圖一般化而來。

## 概念 / Concept

- **輸入 / Input**（每個 journey 一份 `config.json`）：`user_login`、`place_id`、日期區間 `d1`–`d2`。
- **自動分段 / Auto-segment**：一段 query 可能含多趟踏查；依**日期 + 時間間隔**自動切成 **walk**。
- **每趟一張剖面圖 / One transect per walk**：x = 沿步道水平距離、y = 海拔；點 = 該趟觀察。
- **旅程索引 / Journey index**：多趟列成一頁，點進各自剖面圖。
- **健行模式 / Trek mode**（`"mode": "trek"`）：點對點的多日健行＝**一條連續路徑**，跨日合成**單一張**剖面圖（x = 累積里程）。
- 自包含 HTML、套荒野品牌色（見 `../brand/`）。

> ⚠️ 剖面圖本質是**單一路徑**視覺化。**重複踏查同一條路線**（如二格山稜線）→「**N 趟 → N 張圖**」，不跨日合成；
> **點對點健行**（如尼泊爾）→ 連續路徑，刻意以 trek mode 合成單一張。兩者由 config 決定。

## 用法 / Usage

```bash
python3 generate.py --journey erge-2026-04-25
```

讀 `journeys/<id>/config.json` → 抓取 → 分段 → 產出 `site/<id>/`。

### 新增旅程 / Add a journey

- **線上表單 / Hosted form**：GitHub → **Actions** → **Create journey** → Run workflow，填使用者、地點（名稱或 place_id）、日期、模式即可自動產生並部署。執行記錄會列出地點候選 place_id 與偏離路線的離群觀測（供 `exclude_ids` 重跑）。
- **本機 / Local**：`python3 new_journey.py --user U --place "Yushan" --d1 … --d2 … --mode trek`，再 `python3 generate.py --journey <id> && python3 build_site_index.py`。

## 狀態 / Status

| 階段 | 內容 | 狀態 |
|---|---|---|
| P1 | 抓取 + walk 自動分段 → `journey.json` | ✅ |
| P2 | 每趟：GPS 校正 + SRTM 海拔 + 沿步道距離 + 學名 | ✅ |
| P3 | 每趟剖面圖 HTML + 旅程索引 | ✅ |
| P4 | 一般化驗證：trek mode、海外分類（iNat）、自適應 m↔km 軸 | ✅ |

實例 / Instances：
- **二格山稜線 2026-04-25**（survey mode；93 樣點 / 63 種；其長期物候典藏仍留在 `../2G 二格/iNAT in Erge/`）。
- **尼泊爾 2023 喜馬拉雅健行**（trek mode；16 天 query → 一條連續剖面；103 樣點 / 87 種 / 161.8 km / 最高 5628 m）。

🤖 Built with [Claude Code](https://claude.com/claude-code).
