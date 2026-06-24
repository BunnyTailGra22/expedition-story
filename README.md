# Expedition Story

> 把任一段 iNaturalist 踏查（使用者 × 地點 × 日期區間）自動產成「植被海拔剖面圖」網站。
> Turn any iNaturalist survey (user × place × date-range) into a vegetation elevation-transect site.

荒野保護協會 Society of Wilderness · 通用工具，由二格山稜線剖面圖一般化而來。

## 概念 / Concept

- **輸入 / Input**（每個 journey 一份 `config.json`）：`user_login`、`place_id`、日期區間 `d1`–`d2`。
- **自動分段 / Auto-segment**：一段 query 可能含多趟踏查；依**日期 + 時間間隔**自動切成 **walk**。
- **每趟一張剖面圖 / One transect per walk**：x = 沿步道水平距離、y = 海拔；點 = 該趟觀察。
- **旅程索引 / Journey index**：多趟列成一頁，點進各自剖面圖。
- 自包含 HTML、套荒野品牌色（見 `../brand/`）。

> ⚠️ 剖面圖本質是**單一路徑**視覺化；日期區間是「選擇器」，產出的是「**N 趟 → N 張圖**」，不是把跨日合成一張。

## 用法 / Usage

```bash
python3 generate.py --journey erge-2026-04-25
```

讀 `journeys/<id>/config.json` → 抓取 → 分段 → 產出 `site/<id>/`。

## 狀態 / Status

| 階段 | 內容 | 狀態 |
|---|---|---|
| P1 | 抓取 + walk 自動分段 → `journey.json` | ✅ |
| P2 | 每趟：GPS 校正 + SRTM 海拔 + 沿步道距離 + TaiCoL 學名 | ⏳ |
| P3 | 每趟剖面圖 HTML + 旅程索引 + 部署 | ⏳ |

第一個實例 / First instance：**二格山稜線 2026-04-25**（其長期物候典藏仍留在 `../2G 二格/iNAT in Erge/`）。

🤖 Built with [Claude Code](https://claude.com/claude-code).
