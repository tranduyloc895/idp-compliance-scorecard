# Evidence trên AWS

Mỗi lần chạy `aws-up.sh` / `smoke.sh` / `aws-down.sh` tạo một thư mục `<UTC timestamp>-<up|smoke|down>/` với `timings.txt`, `steps.log`, response API, `image-digests.tsv`, `orphans-after.txt`. Không chứa secret.
