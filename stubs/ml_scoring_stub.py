"""
FraudLens - ML Scoring Stub (Giả lập Hot Path)
Thực hiện thẩm định dữ liệu (Data Validation), tính đặc trưng và chấm điểm rủi ro.
Tuân thủ các giá trị routing trong schema: ('LOW', 'MEDIUM', 'HIGH', 'MANUAL_FALLBACK_UNSCORED').
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Tuple


class MLScoringStub:
    MODEL_VERSION = "xgb-fraud-v1.0.0-stub"
    THRESHOLD_CONFIG_VERSION = "th-v2026.1"

    # Thresholds: >= 0.70 -> HIGH, >= 0.35 -> MEDIUM, else -> LOW
    HIGH_THRESHOLD = 0.70
    MEDIUM_THRESHOLD = 0.35

    HIGH_RISK_CATEGORIES = {"misc_net", "shopping_net", "grocery_pos", "entertainment"}

    @classmethod
    def score_transaction(cls, txn_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hàm chấm điểm giao dịch giả lập.
        Trả về: dict chứa risk_score, calibrated_prob, routing, features, model_version, threshold_config_version.
        """
        # 1. Thẩm định dữ liệu (FR-01 Data Validation)
        amt = float(txn_data.get("amt") or 0.0)
        cc_num = txn_data.get("cc_num")
        trans_time = txn_data.get("trans_time")

        # Vi phạm nghiêm trọng: số tiền âm, thiếu số thẻ hoặc thiếu thời gian
        if amt <= 0 or not cc_num or not trans_time:
            return {
                "risk_score": Decimal("0.0000"),
                "calibrated_prob": Decimal("0.0000"),
                "routing": "MANUAL_FALLBACK_UNSCORED",
                "model_version": cls.MODEL_VERSION,
                "threshold_config_version": cls.THRESHOLD_CONFIG_VERSION,
                "features": {
                    "error_reason": "Data validation failed (negative amount or missing vital fields)",
                    "validation_passed": False
                }
            }

        # 2. Giả lập tính toán đặc trưng (Feature Engineering)
        category = str(txn_data.get("category", "")).lower()
        cat_weight = 0.35 if category in cls.HIGH_RISK_CATEGORIES else 0.10

        # Kiểm tra số tiền lớn
        if amt > 800:
            amt_weight = 0.45
        elif amt > 300:
            amt_weight = 0.30
        elif amt > 100:
            amt_weight = 0.15
        else:
            amt_weight = 0.05

        # Giả lập thời gian giao dịch đêm (23h - 5h sáng)
        hour = 12
        if isinstance(trans_time, datetime):
            hour = trans_time.hour
        elif isinstance(trans_time, str):
            try:
                dt = datetime.fromisoformat(trans_time.replace("Z", "+00:00"))
                hour = dt.hour
            except Exception:
                pass
        
        time_weight = 0.20 if (hour >= 23 or hour <= 5) else 0.05

        # Tính toán raw score (tổng hợp trọng số)
        raw_score = min(0.9999, round(cat_weight + amt_weight + time_weight, 4))
        calibrated_prob = min(0.9999, round(raw_score * 0.96, 4))

        # 3. Phân luồng (Triage & Routing - FR-03)
        if raw_score >= cls.HIGH_THRESHOLD:
            routing = "HIGH"
        elif raw_score >= cls.MEDIUM_THRESHOLD:
            routing = "MEDIUM"
        else:
            routing = "LOW"

        # Đóng gói features (SHAP explainability)
        features = {
            "category_risk": cat_weight,
            "amount_deviation": amt_weight,
            "trans_hour_risk": time_weight,
            "shap_summary": [
                {"feature": "amt", "importance": amt_weight, "value": amt},
                {"feature": "category", "importance": cat_weight, "value": category},
                {"feature": "hour_of_day", "importance": time_weight, "value": hour}
            ],
            "validation_passed": True
        }

        return {
            "risk_score": Decimal(str(raw_score)),
            "calibrated_prob": Decimal(str(calibrated_prob)),
            "routing": routing,
            "model_version": cls.MODEL_VERSION,
            "threshold_config_version": cls.THRESHOLD_CONFIG_VERSION,
            "features": features
        }


ml_scorer = MLScoringStub()
