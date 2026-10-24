"""
FraudLens - Simulator Stub
Đọc dataset từ fraudTrain.csv, phát lại các giao dịch mô phỏng theo thứ tự thời gian.
Tách biệt hoàn toàn nhãn 'is_fraud' để chống Data Leakage.
"""
import os
import csv
from datetime import datetime
from decimal import Decimal
from typing import Generator, Dict, Any, List, Optional

CSV_PATH = os.path.join(os.path.dirname(__file__), "fraudTrain.csv")


class SimulatorStub:
    def __init__(self, csv_path: str = CSV_PATH):
        self.csv_path = csv_path

    def stream_transactions(
        self,
        limit: int = 20,
        inject_fault_index: Optional[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Đọc và yield từng giao dịch từ CSV.
        Tách is_fraud sang 'ground_truth_is_fraud'.
        """
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Dataset not found at: {self.csv_path}")

        count = 0
        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if count >= limit:
                    break

                trans_time_str = row.get("trans_date_trans_time", "")
                try:
                    trans_time = datetime.strptime(trans_time_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    trans_time = datetime.now()

                dob_str = row.get("dob")
                dob = None
                if dob_str:
                    try:
                        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
                    except Exception:
                        dob = None

                raw_amt = float(row.get("amt", 0.0))
                # Mô phỏng tiêm lỗi nếu yêu cầu
                if inject_fault_index is not None and count == inject_fault_index:
                    raw_amt = -50.0  # Lỗi số tiền âm

                is_fraud_val = int(row.get("is_fraud", 0))

                txn_dict = {
                    "transaction_id": row.get("trans_num") or f"txn_{count}",
                    "cc_num": row.get("cc_num", ""),
                    "merchant": row.get("merchant", ""),
                    "category": row.get("category", ""),
                    "amt": Decimal(str(raw_amt)),
                    "first_name": row.get("first"),
                    "last_name": row.get("last"),
                    "gender": row.get("gender"),
                    "street": row.get("street"),
                    "city": row.get("city"),
                    "state": row.get("state"),
                    "zip": row.get("zip"),
                    "lat": Decimal(row["lat"]) if row.get("lat") else None,
                    "long": Decimal(row["long"]) if row.get("long") else None,
                    "city_pop": int(row["city_pop"]) if row.get("city_pop") else None,
                    "job": row.get("job"),
                    "dob": dob,
                    "merch_lat": Decimal(row["merch_lat"]) if row.get("merch_lat") else None,
                    "merch_long": Decimal(row["merch_long"]) if row.get("merch_long") else None,
                    "trans_time": trans_time,
                    "unix_time": int(row.get("unix_time", 0)),
                    "ground_truth_is_fraud": bool(is_fraud_val)
                }

                yield txn_dict
                count += 1

    def get_batch(self, size: int = 10, inject_fault: bool = False) -> List[Dict[str, Any]]:
        """Lấy một batch giao dịch để kiểm thử"""
        fault_idx = 2 if inject_fault else None
        return list(self.stream_transactions(limit=size, inject_fault_index=fault_idx))


simulator = SimulatorStub()
