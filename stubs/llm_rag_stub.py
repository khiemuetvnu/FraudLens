"""
FraudLens - LLM & RAG Module Stub (Giả lập Cold Path)
Tổng hợp dữ liệu giao dịch, kết quả ML và quy trình Playbook để sinh Brief & Checklist.
"""
from typing import Dict, Any


class LLMRAGStub:
    PROMPT_VERSION = "prompt-brief-v2.1"
    PLAYBOOK_VERSION = "playbook-v2026.1"

    @classmethod
    def generate_case_brief(cls, transaction: Dict[str, Any], score: Dict[str, Any]) -> Dict[str, Any]:
        """
        Giả lập gọi LLM + RAG để tạo nội dung Case Brief.
        Trả về content JSONB khớp với yêu cầu nghiệp vụ.
        """
        txn_id = transaction.get("transaction_id", "N/A")
        merchant = transaction.get("merchant", "Unknown Merchant")
        amt = transaction.get("amt", 0)
        category = transaction.get("category", "General")
        routing = score.get("routing", "MEDIUM")
        risk_score = float(score.get("risk_score", 0.5))

        # Tóm tắt ngữ cảnh
        summary = (
            f"Giao dịch {txn_id} ghi nhận tại đơn vị chấp nhận thẻ '{merchant}' "
            f"thuộc danh mục '{category}' với số tiền ${amt:.2f}. "
            f"Mô hình ML phát hiện mức rủi ro {routing} ({risk_score:.2%}). "
            f"Khuyến nghị chuyên viên tiến hành kiểm tra quy trình trước khi quyết định xử lý."
        )

        # Giải thích các yếu tố rủi ro
        risk_factors_explained = [
            {
                "factor": "Giá trị giao dịch bất thường",
                "severity": "HIGH" if amt > 500 else "MEDIUM",
                "detail": f"Số tiền giao dịch ${amt:.2f} cao hơn đáng kể so với ngưỡng trung bình danh mục {category}."
            },
            {
                "factor": "Danh mục rủi ro cao",
                "severity": "HIGH" if category in ["misc_net", "shopping_net"] else "LOW",
                "detail": f"Giao dịch trực tuyến qua danh mục {category} có tần suất gian lận cao."
            }
        ]

        # Checklist điều tra bám sát Playbook
        investigation_checklist = [
            {
                "step_id": 1,
                "title": "Kiểm tra lịch sử giao dịch chủ thẻ",
                "action": "Tra cứu các giao dịch lân cận trong 24h qua của số thẻ này xem có dấu hiệu thử thẻ (card testing) hay không.",
                "status": "PENDING",
                "rule_ref": "PB-HIST-01"
            },
            {
                "step_id": 2,
                "title": "Xác minh thông tin định danh & vị trí địa lý",
                "action": "So sánh vị trí merchant và địa chỉ chủ thẻ để phát hiện khoảng cách bất thường.",
                "status": "PENDING",
                "rule_ref": "PB-GEO-02"
            },
            {
                "step_id": 3,
                "title": "Liên hệ chủ thẻ hoặc xác minh OTP",
                "action": "Kiểm tra trạng thái xác thực hai lớp (3D-Secure/OTP) hoặc gọi hotline xác nhận giao dịch.",
                "status": "PENDING",
                "rule_ref": "PB-VERIF-03"
            },
            {
                "step_id": 4,
                "title": "Chuyển cấp Risk Lead nếu số tiền lớn",
                "action": "Nếu phát hiện dấu hiệu gian lận rõ ràng hoặc số tiền > $1000, thực hiện ESCALATE cho Risk Lead.",
                "status": "PENDING",
                "rule_ref": "PB-ESC-04"
            }
        ]

        # Trích dẫn quy trình Playbook
        playbook_citations = [
            {
                "code": "PB-HIST-01",
                "section": "Chương 2.1 - Thẩm định hành vi chủ thẻ",
                "url": "internal://playbook#pb-hist-01"
            },
            {
                "code": "PB-GEO-02",
                "section": "Chương 3.4 - Kiểm tra bất thường địa lý",
                "url": "internal://playbook#pb-geo-02"
            },
            {
                "code": "PB-ESC-04",
                "section": "Chương 5.1 - Tiêu chuẩn chuyển cấp hồ sơ",
                "url": "internal://playbook#pb-esc-04"
            }
        ]

        return {
            "prompt_version": cls.PROMPT_VERSION,
            "playbook_version": cls.PLAYBOOK_VERSION,
            "status": "READY",
            "content": {
                "summary": summary,
                "risk_factors_explained": risk_factors_explained,
                "investigation_checklist": investigation_checklist,
                "playbook_citations": playbook_citations
            }
        }


llm_rag = LLMRAGStub()
