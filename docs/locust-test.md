# Báo cáo kiểm thử tải NewBid88 API

## Link Kaggle: [Locust test - NewBid88](https://www.kaggle.com/code/bakaafk/locust-test-newbid88)

## 1. Mục tiêu, phạm vi và môi trường

Mục tiêu là đo thông lượng và độ trễ của 15 endpoint khi số người dùng đồng thời tăng dần. Locust chạy trên Kaggle, còn server chạy trên máy cá nhân qua một tunnel.

| Thành phần | Chi tiết |
| --- | --- |
| Đường đi | Kaggle notebook  -> Cloudflare quick tunnel (`trycloudflare.com`) -> máy local -> Docker Compose |
| Máy tạo tải | Kaggle, Python 3.13, Locust 2.47.0  1 master + 2 worker (`--processes 2`) |
| Server | Docker Compose: `api` (FastAPI/Uvicorn, cổng 8000) và `db` (PostgreSQL 16); Docker được cấp 3,658 GiB RAM |
| Thời điểm đo | 31/10/2026, 22:59 - 23:11 (10-200 user) và 23:42 - 23:53 (400 và 800 user) |
| Các bậc tải | 10, 25, 50, 100, 200 user (2 phút mỗi bậc) và 400, 800 user (5 phút mỗi bậc); tốc độ sinh 5 user/giây; nghỉ 30 giây giữa các bậc |

## 2. Kịch bản và phương pháp đo

Mỗi người dùng ảo lặp lại một chuỗi thao tác có trọng số, nghỉ ngẫu nhiên 1-3 giây giữa hai yêu cầu (`wait_time = between(1, 3)`). Người dùng chỉ gửi yêu cầu tiếp theo sau khi nhận phản hồi.

| Loại người dùng | Trọng số | Hành vi |
| --- | --- | --- |
| `BidderUser` | 5 | Đăng ký, đăng nhập, nạp tiền, duyệt phiên, đặt giá, xem ví và lịch sử |
| `ReaderUser` | 3 | Khách chưa đăng nhập, chỉ đọc danh sách, chi tiết, lịch sử bid và `/health` |
| `SellerUser` | 1 | Đăng ký, đăng nhập, tạo phiên, tạo rồi xóa phiên, xem phiên của mình |

Mỗi worker tạo sẵn 20 phiên đấu giá khi bắt đầu, nên mỗi bậc có 40 phiên khởi tạo (2 worker). Cờ `--reset-stats` xóa số liệu giai đoạn tăng tải, nên thống kê chỉ tính phần đã ổn định, dài khoảng 74 giây ở bậc 200 user và khoảng 112 giây ở bậc 10 user (tính từ số yêu cầu chia cho thông lượng).

Trên máy local, `docker stats` ghi CPU và RAM của hai container sau mỗi khoảng 4 giây, nên các đỉnh ngắn hơn một chu kỳ có thể bị bỏ sót.

Trước khi chạy tải, `/health` được gọi 30 lần từ Kaggle qua tunnel và 30 lần bằng `curl` ngay trên máy server khi hệ thống rảnh.

| Đường đi | p50 | Lớn nhất |
| --- | --- | --- |
| Kaggle -> tunnel (mỗi yêu cầu mở kết nối mới) | 381 ms | 1.455 ms |
| `curl` trên localhost | 3,5 ms | 11,8 ms |

## 3. Kết quả

API NewBid88 chạy ổn định đến 200 người dùng ảo đồng thời (khoảng 95 yêu cầu/giây, không lỗi), nhưng ở 400 người dùng thông lượng chữ lại quanh 100 yêu cầu/giây, độ trễ tăng gần 5 lần và bắt đầu có lỗi HTTP 429.

- Thông lượng tăng tuyến tính đến 200 user: từ 4,6 req/s (10 user) lên 95,4 req/s (200 user), khoảng 0,48 req/s mỗi user, với 16.050 yêu cầu, 0 lỗi 5xx và 0 timeout.&#32;
- Trần thông lượng khoảng 100-110 req/s: ở 400 user thông lượng thành công chỉ 101 req/s (mô hình dự báo khoảng 180), p50 lên 1,7 s thay vì 0,3 s.
- Lỗi 429 từ 400 user: 6,4% yêu cầu ở 400 user và 63% ở 800 user, thân phản hồi rỗng và đặc tả không có mã này. Nguồn nhiều khả năng là giới hạn 200 yêu cầu đồng thời của Cloudflare quick tunnel (mục 4.4).
- Độ trễ ở mức tải thấp do mạng chi phối: đến 200 user, p50 300-330 ms và p95 460-630 ms. Sau tunnel, độ trễ tối thiểu khoảng 260 ms, trong khi `/health` chạy trực tiếp trên máy chủ chỉ mất khoảng 3,5 ms.
- Đăng ký và đăng nhập là điểm chậm riêng: p50 lên 3,1 s và 2,8 s ở 50 user và kéo p99 toàn hệ thống lên 2,9 s. Nguyên nhân nhiều khả năng là băm bcrypt tốn CPU (mục 4.2).

| User | Số yêu cầu | Thông lượng (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Lớn nhất (ms) | Lỗi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 514 | 4,6 | 330 | 550 | 820 | 1.223 | 0 |
| 25 | 1.298 | 11,9 | 310 | 480 | 1.600 | 2.210 | 0 |
| 50 | 2.574 | 24,9 | 300 | 460 | 2.900 | 3.707 | 0 |
| 100 | 4.614 | 49,3 | 300 | 530 | 1.400 | 10.284 | 0 |
| 200 | 7.050 | 95,4 | 320 | 630 | 980 | 1.584 | 0 |
| 400 | 23.007 | 108,0 | 1.700 | 2.700 | 5.100 | 42.998 | 1.476 (6,4%), HTTP 429 |
| 800 | 23.315 | 174,6 | 290 (\*) | 4.100 | 7.400 | 17.568 | 14.689 (63%), HTTP 429 |

&#32;(\*p50 ở 800 user bị kéo xuống vì hơn một nửa yêu cầu là phản hồi 429 trả về nhanh)

Từ 10 đến 200 user, mọi endpoint đọc và ghi thông thường nằm trong khoảng 280-370 ms, còn ở 400 user chúng chậm đồng loạt lên 1.400-2.000 ms. Riêng `/auth/register` và `/auth/login` cao hơn hẳn và thay đổi theo tải.


| p50 (ms) | 10 user | 25 user | 50 user | 100 user | 200 user | 400 user (**) | 800 user (**) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POST /auth/register` | 970 | 1.700 | 3.100 | 3.500 | 1.500 | 6.600 | 650 |
| `POST /auth/login` | 710 | 1.200 | 2.800 | 2.400 | 1.100 | 640 | 230 |
| Số yêu cầu register / login trong cửa sổ đo | 7 / 7 | 17 / 17 | 33 / 33 | 17 / 31 | 6 / 10 | 28 / 33 | 241 / 91 |

(**) Ở 400 và 800 user, một phần register/login là phản hồi 429 trả về nhanh (register 11 và 156 yêu cầu, login 17 và 73 yêu cầu), nên p50 bị kéo xuống và chỉ mang tính tham khảo, đặc biệt ở 800 user.

## 4. Phân tích

### 4.1 Độ trễ chủ yếu là đường truyền

Độ trễ nhỏ nhất của mọi endpoint là 258-267 ms, và `/health` có p50 280-290 ms qua tunnel nhưng chỉ khoảng 3,5 ms trên localhost. Vậy khoảng 99% thời gian của một yêu cầu đọc đơn giản là thời gian đi qua Internet và tunnel, không phải xử lý ở ứng dụng. Do đó con số p50 trong báo cáo này không dùng để đánh giá tốc độ của API.

Hai endpoint danh sách (`GET /auctions`) và lịch sử bid (`GET /auctions/[id]/bids`) cao hơn `/health` khoảng 80 ms (p50 360 so với 280). Phần chênh này có thể do truy vấn DB hoặc do phản hồi lớn hơn truyền qua tunnel.

### 4.2 Đăng ký và đăng nhập là điểm chậm

Ở 10 user, `register` có p50 970 ms và `login` 710 ms, tức cao hơn sàn mạng khoảng 430-690 ms; ở 50 user chúng lên 3,1 s và 2,8 s. Hai endpoint này chiếm chỉ khoảng 2,6% số yêu cầu ở bậc 50 user nhưng đủ để kéo p99 toàn hệ thống lên 2,9 s trong khi p95 chỉ 460 ms.

Nguyên nhân có thể là do băm và xác thực mật khẩu bằng bcrypt tốn nhiều CPU, và các user đăng ký đồng loạt trong lúc tăng tải phải xếp hàng  (CPU của `api` có đỉnh rất cao trong giai đoạn đó).&#32;

### 4.3 Tài nguyên server

Số liệu từ `docker stats` (CPU tính theo 100% = 1 nhân; trung bình trong giai đoạn ổn định, đỉnh là mẫu cao nhất trong cả bậc):

| User | CPU `api` TB | CPU `api` đỉnh | CPU `db` TB | CPU `db` đỉnh |
| --- | --- | --- | --- | --- |
| 10 | 10% | 47% | 2,5% | 9% |
| 25 | 26% | 224% | 4,6% | 19% |
| 50 | 47% | 472% | 7,6% | 15% |
| 100 | 61% | 555% | 16% | 41% |
| 200 | 109% | 600% | 28% | 98% |
| 400 | 149% | 1.234% | 55% | 150% |
| 800 | 185% | 1.312% | 69% | 218% |

`api` dùng nhiều hơn một nhân khi cao điểm (600% do là Docker được cấp tối thiểu 6 nhân). Bộ nhớ ổn định: `api` từ 78 lên khoảng 94 MiB, `db` từ 39 lên khoảng 54 MiB trong suốt 20 phút, không có dấu hiệu rò rỉ bộ nhớ.

### 4.4 Từ 400 user: trần thông lượng và lỗi 429

Thông lượng thành công chạm trần khoảng 100-110 req/s ở 400 user, giảm xuống 65 req/s ở 800 user, và từ 400 user xuất hiện lỗi HTTP 429.

Ở 400 user, thông lượng thành công chỉ 101 req/s (tổng 108 req/s), trong khi mô hình 0,48 req/s mỗi user cho khoảng 180 req/s với 372 user còn hoạt động. p50 tăng từ 320 ms lên 1.700 ms và mọi endpoint chậm đồng loạt, kể cả `/health` (p50 1.400 ms). Ở 800 user, thông lượng thành công còn khoảng 65 req/s trong tổng 175 req/s gửi đi, phần còn lại (khoảng 110 req/s) bị từ chối.

Toàn bộ 1.476 lỗi ở 400 user (6,4%) và 14.689 lỗi ở 800 user (63%) đều là HTTP 429. Tài liệu của Cloudflare nêu mỗi Quick Tunnel hỗ trợ tối đa 200 yêu cầu đang xử lý đồng thời, yêu cầu vượt mức nhận phản hồi 429. Số yêu cầu đang xử lý xấp xỉ thông lượng nhân thời gian phản hồi: ở 200 user chỉ khoảng 95 × 0,33 ≈ 30 nên không bao giờ chạm trần; ở 400 user khoảng 101 × 1,7 ≈ 170, sát 200 nên bị chạm lúc cao điểm (429 rải rác vài req/s); ở 800 user trần bị chạm liên tục và khoảng 110 req/s bị từ chối. Đây là giới hạn do luồng nghiệp vụ chứ không phải giới hạn của hệ thống.

Mặt khác, ngay khi chưa có lỗi nào (80-320 user), p50 ở bậc 400 đã là 1,1-2,6 giây, và CPU `api` trung bình 431% trong 85 giây tăng tải (608% ở bậc 800). Đây là lúc hàng chục user mới phải đăng ký và đăng nhập mỗi giây, phù hợp với giả thuyết ở mục 4.2.

## 5. Hạn chế và mức tin cậy

Các kết luận ở trên đúng cho điều kiện đo này, và cần đọc kèm các giới hạn sau.

- Đường truyền che mất hiệu năng ứng dụng: Khoảng 260 ms mỗi yêu cầu là mạng, nên mọi khác biệt dưới vài chục ms giữa các endpoint không đáng tin.
- Trần quan sát được (khoảng 100-110 req/s) chưa quy được cho thành phần nào. Giới hạn 200 yêu cầu đồng thời của quick tunnel, một worker Python và pool kết nối DB đều khớp số liệu.&#32;
- Tải thực tế thấp hơn mục tiêu ở 400 và 800 user. Locustfile dừng user khi đăng ký hoặc đăng nhập thất bại: 28 user ở bậc 400 và khoảng 230 user ở bậc 800, nên chỉ còn 372 và 568 user.&#32;
- Độ trễ ở 800 user không đại diện cho API. 63% phản hồi là 429 trả về trong khoảng 240 ms, nên p50 290 ms không phản ánh yêu cầu thành công.
- Đo CPU thưa. Khoảng 4 giây một mẫu, nên các đỉnh ngắn có thể bị bỏ sót

## 
