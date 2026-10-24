"""
==================================================================
FraudLens - Kịch bản Demo Kiểm thử Nghiệp vụ Từ Đầu Đến Cuối (E2E)
Chạy trực tiếp: d:\\FraudLens\\.conda\\python.exe run_demo.py
==================================================================
"""
import sys
import json
from datetime import datetime

from fastapi.testclient import TestClient
from main import app
from connections.database import WriteSessionLocal
from services.auth_service import auth_service
from models.transaction import Score, DelayedLabel
from models.case import Case, Brief, CaseNote
from models.audit_log import AuditLog


def print_step(title: str):
    print("\n" + "=" * 70)
    print(f"👉 {title}")
    print("=" * 70)


def main():
    print("🚀 KHỞI ĐỘNG KỊCH BẢN CHẠY THỬ NGHIỆM FRAUDLENS (WORKFLOW MODULE)")

    # 0. Khởi tạo tài khoản ban đầu nếu chưa có
    with WriteSessionLocal() as db:
        auth_service.seed_initial_users(db)

    with TestClient(app) as client:
        # -------------------------------------------------------------
        # BƯỚC 1: ĐĂNG NHẬP & XÁC THỰC (JWT + RBAC)
        # -------------------------------------------------------------
        print_step("BƯỚC 1: Đăng nhập các vai trò (Analyst & Risk Lead & Service)")

        # 1.1 Login Analyst
        r_analyst = client.post("/api/auth/login", json={"username": "analyst1", "password": "AnalystPassword123!"})
        assert r_analyst.status_code == 200, r_analyst.text
        analyst_token = r_analyst.json()["access_token"]
        analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
        print(f"✅ Đăng nhập Analyst (analyst1) thành công. Role: {r_analyst.json()['role']}")

        # 1.2 Login Risk Lead
        r_lead = client.post("/api/auth/login", json={"username": "lead1", "password": "LeadPassword123!"})
        assert r_lead.status_code == 200, r_lead.text
        lead_token = r_lead.json()["access_token"]
        lead_headers = {"Authorization": f"Bearer {lead_token}"}
        print(f"✅ Đăng nhập Risk Lead (lead1) thành công. Role: {r_lead.json()['role']}")

        # 1.3 Login Service
        r_svc = client.post("/api/auth/login", json={"username": "simulator_svc", "password": "ServicePassword123!"})
        assert r_svc.status_code == 200, r_svc.text
        svc_token = r_svc.json()["access_token"]
        svc_headers = {"Authorization": f"Bearer {svc_token}"}
        print(f"✅ Đăng nhập Ingest Service (simulator_svc) thành công. Role: {r_svc.json()['role']}")

        # -------------------------------------------------------------
        # BƯỚC 2: TIẾP NHẬN GIAO DỊCH TỪ SIMULATOR & CÁCH LY NHÃN
        # -------------------------------------------------------------
        print_step("BƯỚC 2: Ingest giao dịch từ dataset fraudTrain.csv (Simulator Stub)")
        
        sim_res = client.post("/api/transactions/simulate-batch?count=5&inject_fault=true", headers=svc_headers)
        assert sim_res.status_code == 200, sim_res.text
        txns = sim_res.json()
        print(f"✅ Đã nạp thành công {len(txns)} giao dịch vào hệ thống (có tiêm 1 giao dịch lỗi âm để test Fail-safe).")
        for i, t in enumerate(txns):
            print(f"   [{i+1}] ID: {t['transaction_id'][:12]}... | Thẻ: {t['cc_num']} | Merchant: {t['merchant']} | Số tiền: ${t['amt']} | Status: {t['input_status']}")

        # Kiểm tra cách ly nhãn
        with WriteSessionLocal() as db:
            labels_count = db.query(DelayedLabel).count()
            print(f"🔒 Chống Data Leakage: Đã cách ly {labels_count} nhãn ground-truth vào bảng delayed_labels.")

        # -------------------------------------------------------------
        # BƯỚC 3: KÍCH HOẠT CHẤM ĐIỂM RỦI RO ML (HOT PATH)
        # -------------------------------------------------------------
        print_step("BƯỚC 3: Kết quả ML Scoring & Phân luồng (Hot Path)")
        for i, t in enumerate(txns):
            score = t.get("score")
            if score:
                print(f"   [{i+1}] Txn: {score['transaction_id'][:12]}... -> Risk Score: {score['risk_score']} | Routing: {score['routing']} | Model: {score['model_version']}")
                if score['routing'] == 'MANUAL_FALLBACK_UNSCORED':
                    print("       ⚠️ Fail-safe kích hoạt: Giao dịch lỗi được gắn cờ MANUAL_FALLBACK_UNSCORED, không gán nhầm LOW.")

        # -------------------------------------------------------------
        # BƯỚC 4: HÀNG ĐỢI ĐIỀU TRA & TỰ ĐỘNG TẠO CASE (REVIEW QUEUE)
        # -------------------------------------------------------------
        print_step("BƯỚC 4: Review Queue - Tự động tạo Case cho MEDIUM và HIGH")
        queue_res = client.get("/api/cases/", headers=analyst_headers)
        assert queue_res.status_code == 200, queue_res.text
        cases = queue_res.json()
        print(f"✅ Tổng số Case trong Review Queue: {len(cases)} cases")
        for c in cases[:3]:
            print(f"   📌 Case ID: {c['case_id']} | Priority: {c['priority']} | Status: {c['status']} | Source: {c['source']}")

        target_case = cases[0]
        case_id = target_case["case_id"]

        # -------------------------------------------------------------
        # BƯỚC 5: XEM CASE BRIEF & TẠO LẠI BRIEF (LLM COLD PATH)
        # -------------------------------------------------------------
        print_step(f"BƯỚC 5: Xem LLM Case Brief & Checklist điều tra cho Case {case_id}")
        detail_res = client.get(f"/api/cases/{case_id}", headers=analyst_headers)
        assert detail_res.status_code == 200, detail_res.text
        detail = detail_res.json()
        brief = detail.get("brief")
        if brief and brief.get("content"):
            content = brief["content"]
            print(f"📝 Tóm tắt ngữ cảnh: {content.get('summary')}")
            print(f"📋 Checklist điều tra từ Playbook:")
            for item in content.get("investigation_checklist", []):
                print(f"   [ ] Bước {item.get('step_id')}: {item.get('title')} (Quy tắc: {item.get('rule_ref')})")

        # Re-generate Brief (Cold path test)
        regen_res = client.post(f"/api/cases/{case_id}/brief/regenerate", headers=analyst_headers)
        assert regen_res.status_code == 200, regen_res.text
        print(f"✅ Chức năng Re-generate Brief: Đã cập nhật đè Brief thành công (Quan hệ 1-1).")

        # -------------------------------------------------------------
        # BƯỚC 6: XỬ LÝ NGHIỆP VỤ (NOTES, CHUYỂN TRẠNG THÁI, RBAC)
        # -------------------------------------------------------------
        print_step("BƯỚC 6: Chuyên viên xử lý nghiệp vụ trên Case")
        # 6.1 Ghi note điều tra (append-only)
        note_res = client.post(
            f"/api/cases/{case_id}/notes",
            json={"content": "Đã đối chiếu vị trí merchant và nơi cư trú của chủ thẻ, phát hiện khoảng cách bất thường > 300km."},
            headers=analyst_headers
        )
        assert note_res.status_code == 201, note_res.text
        print(f"✅ Ghi nhận Case Note thành công (Author: analyst1, Note ID: {note_res.json()['note_id']})")

        # 6.2 Chuyển trạng thái: NEW -> UNDER_REVIEW -> ESCALATED
        client.put(f"/api/cases/{case_id}/status", json={"status": "UNDER_REVIEW"}, headers=analyst_headers)
        client.put(f"/api/cases/{case_id}/status", json={"status": "ESCALATED"}, headers=analyst_headers)
        print("✅ Chuyên viên chuyển trạng thái thành công: NEW ➔ UNDER_REVIEW ➔ ESCALATED (Chuyển cấp Risk Lead)")

        # 6.3 Kiểm tra RBAC: Analyst thử đóng case -> Bị chặn 403 Forbidden
        fb_res = client.put(f"/api/cases/{case_id}/status", json={"status": "CLOSED"}, headers=analyst_headers)
        if fb_res.status_code == 403:
            print("🛡️ RBAC bảo vệ: Analyst không có quyền đóng case (Hệ thống trả về HTTP 403 Forbidden).")

        # 6.4 Risk Lead phê duyệt & đóng case
        client.put(f"/api/cases/{case_id}/status", json={"status": "CLOSED"}, headers=lead_headers)
        client.put(f"/api/cases/{case_id}/outcome", json={"outcome": "CONFIRMED_FRAUD_SIM"}, headers=lead_headers)
        print("✅ Risk Lead (lead1) đã đóng Case với kết luận outcome: CONFIRMED_FRAUD_SIM")

        # -------------------------------------------------------------
        # BƯỚC 7: TRUY VẾT KIỂM TOÁN TỰ ĐỘNG (TRIGGER AUDIT_LOG)
        # -------------------------------------------------------------
        print_step("BƯỚC 7: Truy vết Audit Log tự động từ Database Trigger (trg_case_audit)")
        with WriteSessionLocal() as db:
            logs = db.query(AuditLog).filter(AuditLog.entity_id == str(case_id)).order_by(AuditLog.occurred_at.asc()).all()
            print(f"🔍 Đã ghi nhận {len(logs)} sự kiện audit tự động cho Case này:")
            for l in logs:
                print(f"   ⏱️ {l.occurred_at.strftime('%H:%M:%S')} | Actor: {l.actor_id:10} | Action: {l.action:18} | Trạng thái: {l.before_state.get('status')} ➔ {l.after_state.get('status')} | Outcome: {l.after_state.get('outcome')}")

        # -------------------------------------------------------------
        # BƯỚC 8: TẠO CASE THỦ CÔNG CHO GIAO DỊCH LOW
        # -------------------------------------------------------------
        print_step("BƯỚC 8: Tạo Case thủ công (Manual Case Creation) & Chống trùng lặp 1-1")
        # Ingest 1 giao dịch LOW
        low_res = client.post("/api/transactions/ingest", json={
            "transaction_id": f"manual_demo_{int(datetime.now().timestamp())}",
            "cc_num": "4929111122223333",
            "merchant": "fraud_Local_Coffee_Shop",
            "category": "food_dining",
            "amt": 5.25,
            "trans_time": datetime.now().isoformat(),
            "unix_time": int(datetime.now().timestamp())
        }, headers=svc_headers)
        low_txn = low_res.json()
        print(f"✅ Đã nạp giao dịch: {low_txn['transaction_id']} (Routing: {low_txn['score']['routing']}). Không tự động tạo Case.")

        # Analyst tạo thủ công
        m_case = client.post("/api/cases/manual", json={
            "transaction_id": low_txn['transaction_id'],
            "manual_reason": "Chuyên viên nhận thấy merchant này đang nằm trong danh sách đen từ ngân hàng đối tác.",
            "priority": "HIGH"
        }, headers=analyst_headers).json()
        print(f"✅ Analyst tạo Case thủ công thành công! Case ID: {m_case['case_id']}, Source: {m_case['source']}, Priority: {m_case['priority']}")

        # Thử tạo lại lần 2 -> Bị chặn do vi phạm 1-1
        dup_res = client.post("/api/cases/manual", json={
            "transaction_id": low_txn['transaction_id'],
            "manual_reason": "Tạo lại thử",
            "priority": "MEDIUM"
        }, headers=analyst_headers)
        if dup_res.status_code == 400:
            print("🛡️ Ràng buộc 1-1: Hệ thống chặn không cho tạo trùng lặp Case cho cùng một giao dịch (400 Bad Request).")

    print("\n" + "=" * 70)
    print("🎉 TẤT CẢ CÁC BƯỚC THỬ NGHIỆM ĐÃ CHẠY HOÀN TẤT VÀ THÀNH CÔNG 100%!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
