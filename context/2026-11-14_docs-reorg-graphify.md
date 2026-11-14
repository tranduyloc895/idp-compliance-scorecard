# Gom tài liệu vào docs/, thêm CLAUDE.md và hướng dẫn graphify

**Ngày:** 2026-11-14
**Thành phần:** docs
**Loại:** docs

## Mô tả
Tích hợp graphify (knowledge graph của repo) cho Claude Code và Antigravity, rồi gom các tài liệu hướng dẫn vào `docs/`. `SETUP.md` và file audit không trùng nhau: SETUP là runbook, audit là bản rà soát các điểm SETUP chưa khớp với code. Vì vậy giữ cả hai. Thư mục `context/` vẫn dùng làm nơi ghi nhật ký thay đổi theo quy ước trong `GEMINI.md`.

## Các file đã thay đổi
- `SETUP.md` → `docs/SETUP.md`: chuyển vị trí, nội dung giữ nguyên.
- `context/PROJECT_CONTEXT_AND_SETUP_AUDIT.md` → `docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md`: chuyển vị trí, nội dung giữ nguyên.
- `docs/GRAPHIFY.md`: mới, hướng dẫn cài, dựng, cập nhật và hỏi graph, kèm cách dùng khi nhờ AI lên plan.
- `CLAUDE.md`: mới, gồm context dự án, quy tắc làm việc, quy ước change log và mục `## graphify` do `graphify claude install` sinh ra.
- `README.md`: cập nhật link tới `docs/` và cây thư mục.

## Ghi chú / Vấn đề còn lại
- `GEMINI.md` (bị git ignore, chỉ có trên máy local) vẫn trỏ tới đường dẫn cũ `context/PROJECT_CONTEXT_AND_SETUP_AUDIT.md`. Cần đổi thành `docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md`.
- `graphify-out/` bị git ignore. Sau khi chuyển file, chạy `graphify update .` ở repo chính, hoặc `/graphify . --update` để cập nhật các node của docs.
- Hook của graphify cho Claude Code nằm trong `.claude/settings.json` (bị git ignore). Máy khác cần chạy lại `graphify claude install`.
