# Hướng dẫn dùng graphify trong dự án

[graphify](https://github.com/Graphify-Labs/graphify) dựng toàn bộ code và tài liệu của repo thành một knowledge graph. AI (Claude Code, Antigravity) hỏi graph này thay vì grep và đọc từng file, nên nắm context nhanh hơn và tốn ít token hơn.

## 1. Graph nằm ở đâu

Graph nằm trong `graphify-out/` ở thư mục gốc repo. Thư mục này **bị git ignore**, nên mỗi máy phải tự dựng hoặc copy sang.

| File | Dùng để |
|---|---|
| `graph.json` | Dữ liệu graph; các lệnh `query`, `path`, `explain` đọc file này |
| `GRAPH_REPORT.md` | Báo cáo tổng quan: god nodes, community, liên kết bất ngờ, câu hỏi gợi ý |
| `graph.html` | Graph tương tác, mở bằng trình duyệt (graph lớn nên hiển thị theo community) |
| `cache/` | Cache theo hash nội dung; lần dựng sau chỉ xử lý file đã đổi |
| `manifest.json` | Danh sách file đã trích xuất, dùng cho `--update` |

File `.graphifyignore` ở thư mục gốc (cú pháp như `.gitignore`) liệt kê các đường dẫn graphify bỏ qua. Hiện đang bỏ `.yarn/`, vì file yarn release đóng gói sẵn sinh ra hàng nghìn node vô nghĩa.

## 2. Cài đặt (một lần mỗi máy)

Cần Python 3.10 trở lên.

```bash
pip install graphifyy
graphify install
```

- Gói trên PyPI tên `graphifyy` (hai chữ y), còn lệnh là `graphify`.
- `graphify install` cài skill cho Claude Code vào `~/.claude/skills/graphify/`.
- Cho Antigravity: `graphify install --platform antigravity-windows`.
- Để đọc được file Terraform: `pip install "graphifyy[terraform]"`.
- Windows: nếu không gọi được `graphify`, thêm thư mục `Scripts` của Python vào PATH, hoặc cài bằng `pipx install graphifyy`.

Riêng trong repo này, `CLAUDE.md` đã có mục `## graphify`, kèm hook trong `.claude/settings.json` (file này bị git ignore, nên máy khác phải chạy lại `graphify claude install`).

## 3. Dựng và cập nhật graph

Các lệnh có dấu `/` gõ trong Claude Code, các lệnh còn lại chạy trong terminal ở thư mục gốc repo.

| Tình huống | Lệnh |
|---|---|
| Dựng lần đầu (code dùng AST, docs và ảnh dùng LLM) | `/graphify .` |
| Sau khi sửa docs hoặc thêm tài liệu | `/graphify . --update` |
| Sau khi sửa code (chỉ AST, không tốn token) | `graphify update .` |
| Sau khi xóa hoặc đổi tên nhiều file (cho phép graph nhỏ đi) | `graphify update . --force` |
| Tự cập nhật sau mỗi commit, checkout, merge | `graphify hook install` |

Lưu ý:
- Lần dựng đầu cho cả repo tốn khoảng 1,2 triệu token, chủ yếu cho 38 docs và 16 ảnh. Các lần sau dùng cache, gần như miễn phí.
- Git hook chỉ cập nhật phần code. Khi docs thay đổi, chạy `/graphify . --update`.
- Graph có hơn 5.000 node nên `graph.html` chỉ hiện từng community. Muốn xem chi tiết từng node thì dùng `/graphify . --obsidian` hoặc `graphify export wiki`.

## 4. Hỏi graph

| Mục đích | Lệnh |
|---|---|
| Bối cảnh rộng quanh một chủ đề | `graphify query "Backstage plugin lấy score từ đâu?"` |
| Lần theo một luồng cụ thể | `graphify query "luồng scan từ collector tới score" --dfs` |
| Giới hạn độ dài câu trả lời | `graphify query "..." --budget 1500` |
| Đường đi giữa hai thành phần | `graphify path "ComplianceClient" "get_latest_scores"` |
| Giải thích một node và các node xung quanh | `graphify explain "AIRecommender"` |
| Những gì bị ảnh hưởng nếu sửa X | `graphify affected "UnifiedComplianceFinding"` |

Trong Claude Code có thể gõ dạng `/graphify query "..."`. AI sẽ chạy lệnh rồi giải thích kết quả theo cấu trúc graph.

Kết quả ghi rõ mức độ tin cậy của từng quan hệ:
- `EXTRACTED`: có trong code hoặc tài liệu (import, lời gọi hàm, trích dẫn).
- `INFERRED`: AI suy ra, kèm điểm tin cậy.
- `AMBIGUOUS`: chưa chắc, cần kiểm tra lại.

## 5. Dùng graph khi nhờ AI lên plan

1. Mở session ở **repo chính**. Nếu chỉ lên plan thì nên tắt worktree và bật Plan mode để AI chỉ đọc, không sửa file.
2. Viết yêu cầu kèm phạm vi, ví dụ:
   > Dùng graphify để nắm luồng collector → normalizer → scorer → recommender, đọc `docs/PROJECT_CONTEXT_AND_SETUP_AUDIT.md`, rồi lên plan thêm collector cho Falco. Liệt kê file cần sửa và các thành phần bị ảnh hưởng.
3. Vì `CLAUDE.md` đã có mục graphify, Claude tự chạy `graphify query` trước khi grep. Không cần nhắc lại mỗi lần.
4. Kết hợp hai nguồn: graph cho biết code nối với nhau thế nào; `docs/SETUP.md`, audit và các log trong `context/` cho biết mục tiêu và trạng thái thật.
5. Sau khi code xong: commit (nếu đã cài hook) hoặc chạy `graphify update .` để session sau dùng graph mới.

## 6. Hạn chế hiện tại

- **File `.sql`:** parser SQL bị Windows Application Control chặn DLL, nên các file `.sql` không có trong graph.
- **File `secret.yaml`:** graphify tự bỏ qua vì coi là file nhạy cảm.
- **Bundle minify:** loại này làm graph phình to. Nếu sau này có thêm, đưa đường dẫn vào `.graphifyignore`.
- **Tên community:** có khoảng 270 tên được đặt tự động theo đường dẫn file. Tên của các community chính được đặt tay trong lần dựng đầu.
