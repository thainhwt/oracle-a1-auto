# Tự thử tạo Oracle A1 cho Snoopy

Fork từ [WendyChen330/oci-arm-retry](https://github.com/WendyChen330/oci-arm-retry). Bản này chỉ dùng workflow `OCI ARM Retry` để thử tạo **một** máy `VM.Standard.A1.Flex` tên `snoopy-a1`: **1 OCPU, 6 GB RAM, boot volume 50 GB**, Ubuntu 22.04 Arm, trong **subnet hiện có**. Không tự tạo VCN hoặc mở thêm cổng.

## Chuẩn bị

1. Trong Oracle Cloud Console, tạo **API signing key** tại My profile → Tokens and keys → Add API key. Giữ file private key `.pem` và sao chép đoạn cấu hình gồm `user`, `fingerprint`, `tenancy`, `region`.
2. Xác định **compartment OCID** mà máy mới sẽ được tạo vào và **subnet OCID** của public subnet hiện có (có thể xem trong Primary VNIC của VPS cũ). Subnet cần cho phép cấp public IP. Với cấu hình này, subnet và máy mới phải ở cùng compartment.
3. Chuẩn bị cặp **SSH key để vào máy mới**. Giữ private key trên máy của bạn, dùng nội dung file `.pub` cho secret bên dưới. SSH key và OCI API signing key là hai loại khóa khác nhau.

## Thêm GitHub Actions secrets

Vào **Settings → Secrets and variables → Actions → New repository secret** của repo này và tạo đúng tám mục:

| Tên secret | Giá trị |
| --- | --- |
| `OCI_USER` | `user` OCID từ đoạn cấu hình API key |
| `OCI_FINGERPRINT` | `fingerprint` từ đoạn cấu hình API key |
| `OCI_TENANCY` | `tenancy` OCID từ đoạn cấu hình API key |
| `OCI_REGION` | Region, ví dụ `ap-singapore-1` |
| `OCI_PRIVATE_KEY` | **Toàn bộ nội dung** file API private key `.pem`, gồm cả dòng BEGIN/END |
| `OCI_COMPARTMENT_ID` | Compartment OCID để tạo máy (có thể bằng tenancy OCID nếu dùng root) |
| `OCI_SUBNET_ID` | OCID của public subnet hiện có |
| `A1_SSH_PUBLIC_KEY` | **Một dòng đầy đủ** từ file SSH `.pub` của bạn |

Không commit private key hay `.env` vào repo. Bản này **không cần `GH_PAT`**.

## Chạy và kiểm tra

Vào **Actions → OCI ARM Retry → Run workflow**. Workflow thử tạo A1 mỗi 300 giây khi Oracle báo `Out of host capacity`. Mỗi phiên tối đa khoảng 5,5 giờ, sau đó workflow tự khởi động phiên tiếp theo. Khi thấy A1 cùng tên đang tồn tại, nó dừng và tự vô hiệu hóa workflow. Lỗi cấu hình, quyền, quota hoặc các lỗi API khác sẽ dừng để bạn xem log, thay vì lặp vô hạn.

Nếu chuỗi phiên bị gián đoạn, vào Actions để kiểm tra và chạy lại thủ công. Sau khi thành công, mở Oracle Cloud Console → Compute → Instances để lấy public IP. Kiểm tra SSH vào được trước khi chuyển Snoopy. Bản backup boot volume x86 của VPS cũ không thể dùng trực tiếp để khởi động máy A1 Arm; cần chuyển mã nguồn, dữ liệu và cấu hình sang Ubuntu Arm.

Script `oci_retry_micro.py` và workflow Micro của fork gốc không dùng cho việc tạo A1 này; đừng chạy workflow Micro.
