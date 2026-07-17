# -*- coding: utf-8 -*-
"""
Tiền xử lý dữ liệu từ file Excel gốc thành CSV sạch phục vụ MapReduce và ML.
Đã loại bỏ hardcode đường dẫn, sử dụng tham số CLI để chạy linh hoạt trên mọi máy.
"""
import argparse
import sys
import os
from pathlib import Path
import pandas as pd

# Import schema dùng chung
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import FEATURE_COLUMNS, RAW_TO_CANONICAL, LABELS, LEVEL_ENCODING  # noqa: E402

# Lấy 21 biến số (loại trừ age, gender)
NUMERIC_FEATURE_COLUMNS = FEATURE_COLUMNS
RISK_SCALE_COLUMNS = [c for c in NUMERIC_FEATURE_COLUMNS if c not in {"age", "gender"}]

IDENTIFICATION_COLUMNS = ["patient_id"]


def load_source_dataset(data_path: Path) -> pd.DataFrame:
    """Load the raw Excel dataset and validate the expected source schema."""
    df_raw = pd.read_excel(data_path)
    expected_columns = list(RAW_TO_CANONICAL.keys())
    # Kiểm tra xem có cột nào bị thiếu so với schema mong đợi hay không
    missing_columns = [column for column in expected_columns if column not in df_raw.columns]
    # Kiểm tra xem có cột lạ/thừa nào xuất hiện ngoài thiết kế hay không
    unexpected_columns = [column for column in df_raw.columns if column not in expected_columns]

    # Nếu có bất kỳ sự bất nhất nào về cột (thiếu hoặc thừa cột)
    if missing_columns or unexpected_columns:
        # Ném ra ngoại lệ ValueError để thông báo cấu trúc file Excel không hợp lệ
        raise ValueError(
            "Source schema mismatch. "
            f"Missing columns: {missing_columns}. "
            f"Unexpected columns: {unexpected_columns}."
        )

    # Trả về bản sao dữ liệu chỉ chứa các cột đã được định nghĩa trong schema mong đợi
    return df_raw[expected_columns].copy()


def standardize_schema(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Đổi tên các cột thô trong Excel thành định dạng snake_case chuẩn hoá."""
    # rename() nhận vào từ điển ánh xạ RAW_TO_CANONICAL (ví dụ: 'Age' -> 'age')
    return df_raw.rename(columns=RAW_TO_CANONICAL).copy()


def clean_text_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch các trường văn bản: cắt khoảng trắng thừa và chuẩn hoá định dạng chữ."""
    cleaned = df.copy()
    # Ép kiểu patient_id về string và loại bỏ khoảng trắng hai đầu (.str.strip)
    cleaned["patient_id"] = cleaned["patient_id"].astype(str).str.strip()
    # Ép kiểu level về string, loại bỏ khoảng trắng và chuyển chữ cái đầu thành viết hoa (.str.title)
    cleaned["level"] = cleaned["level"].astype(str).str.strip().str.title()
    return cleaned


def cast_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ép kiểu dữ liệu của 23 cột đặc trưng về dạng số thực (float/int)."""
    casted = df.copy()
    # Duyệt qua từng cột trong danh sách đặc trưng số
    for column in NUMERIC_FEATURE_COLUMNS:
        # pd.to_numeric chuyển đổi giá trị sang kiểu số.
        # errors="coerce" sẽ biến các giá trị lỗi (chữ, ô trống) thành NaN (giá trị rỗng) thay vì báo lỗi dừng chương trình.
        casted[column] = pd.to_numeric(casted[column], errors="coerce")
    return casted


def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Xây dựng báo cáo chất lượng dữ liệu dựa trên các quy tắc kiểm định."""
    # Tính tổng số ô dữ liệu bị vượt ngoài thang điểm 1-9 trên 21 cột chỉ số nguy cơ
    # (~df[column].between(1, 9)).sum() đếm số ô không nằm trong khoảng [1, 9]
    invalid_risk_scale = sum(
        (~df[column].between(1, 9)).sum() for column in RISK_SCALE_COLUMNS
    )
    # Khởi tạo danh sách các phép kiểm tra chất lượng (check_name, giá trị đếm lỗi, mô tả ý nghĩa)
    checks = [
        (
            "invalid_gender",
            # Đếm số bản ghi có giới tính không thuộc {1, 2}
            int((~df["gender"].isin([1, 2])).sum()),
            "Count of records where gender is not in {1, 2}.",
        ),
        (
            "invalid_age",
            int((~df["age"].between(0, 120)).sum()),
            "Count of records where age falls outside [0, 120].",
        ),
        (
            "invalid_risk_scale",
            int(invalid_risk_scale),
            "Total instances across 21 risk/symptom columns outside [1, 9].",
        ),
        (
            "invalid_level",
            int((~df["level"].isin(LABELS)).sum()),
            "Count of records where level is not Low, Medium, or High.",
        ),
        ("row_count", int(len(df)), "Rows preserved after preprocessing."),
        ("column_count_clean", int(df.shape[1]), "Columns after schema standardization."),
        ("missing_total", int(df.isna().sum().sum()), "Total missing values after coercion."),
        (
            "duplicated_patient_id",
            int(df["patient_id"].duplicated().sum()),
            "Duplicate patient_id count for business-key monitoring.",
        ),
    ]
    return pd.DataFrame(checks, columns=["check_name", "value", "meaning"])


def add_age_group(df: pd.DataFrame) -> pd.DataFrame:
    """Create MapReduce-ready 10-year age bands."""
    enriched = df.copy()
    enriched["age_group"] = pd.cut(
        enriched["age"],
        bins=[0, 19, 29, 39, 49, 59, 120],
        labels=["<20", "20-29", "30-39", "40-49", "50-59", ">=60"],
        right=True,
        include_lowest=True,
    ).astype("string")
    return enriched


def add_encoded_label(df: pd.DataFrame) -> pd.DataFrame:
    """Create the ordinal tree-model target while keeping the text label."""
    enriched = df.copy()
    # P0-01: Ensure consistency using LEVEL_ENCODING from schema
    enriched["level_encoded"] = enriched["level"].map(LEVEL_ENCODING).astype("Int64")
    return enriched


def build_output_frames(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build HDFS and ML-ready dataframes with all patient rows preserved."""
    hdfs_columns = IDENTIFICATION_COLUMNS + NUMERIC_FEATURE_COLUMNS + ["age_group", "level"]
    ml_columns = IDENTIFICATION_COLUMNS + NUMERIC_FEATURE_COLUMNS + [
        "level_encoded",
        "level",
    ]
    return df[hdfs_columns].copy(), df[ml_columns].copy()


def print_statistical_verification(df: pd.DataFrame) -> None:
    """Print baseline distributions and cross-tabulations from the report."""
    level_distribution = df["level"].value_counts().rename_axis("level").reset_index(
        name="count"
    )
    level_distribution["ratio"] = level_distribution["count"] / len(df)

    print("\nLevel distribution:")
    print(level_distribution.to_string(index=False))

    print("\nAge group x level:")
    print(pd.crosstab(df["age_group"], df["level"]).to_string())

    print("\nSmoking x level:")
    print(pd.crosstab(df["smoking"], df["level"]).to_string())


def main():
    # Khởi tạo bộ phân tích tham số dòng lệnh CLI
    parser = argparse.ArgumentParser(description="Tiền xử lý dữ liệu ung thư.")
    parser.add_argument("--input", required=True, help="Đường dẫn file Excel gốc")
    parser.add_argument("--outdir", required=True, help="Thư mục đầu ra cho các file CSV")
    parser.add_argument("--fail-on-invalid", action="store_true", help="Dừng chương trình nếu dữ liệu không hợp lệ")
    args = parser.parse_args()

    # Khởi tạo các đường dẫn thư mục và file đầu ra
    data_path = Path(args.input)
    output_dir = Path(args.outdir)
    # Tạo thư mục đầu ra nếu chưa tồn tại (bao gồm cả thư mục cha)
    output_dir.mkdir(parents=True, exist_ok=True)

    HDFS_OUTPUT = output_dir / "cancer_patients_clean_hdfs.csv"
    ML_OUTPUT = output_dir / "cancer_patients_ml_ready.csv"
    QUALITY_OUTPUT = output_dir / "cancer_cleaning_quality_report.csv"

    print(f"Reading dataset from {data_path}...")
    # Bước 1: Đọc tệp Excel gốc và kiểm tra cấu trúc cột
    df = load_source_dataset(data_path)
    # Bước 2: Chuẩn hóa tên cột sang snake_case
    df = standardize_schema(df)
    # Bước 3: Làm sạch khoảng trắng dữ liệu chuỗi (patient_id, level)
    df = clean_text_fields(df)
    # Bước 4: Ép kiểu số cho 23 cột đặc trưng (và chuyển giá trị lỗi thành NaN)
    df = cast_numeric_features(df)
    
    # Bước 5: Chạy các bài kiểm định chất lượng dữ liệu để phát hiện lỗi
    quality_report = build_quality_report(df)
    
    # Kiểm tra P0-13: Fail-fast policy (Chính sách Dừng Sớm)
    # Cộng tổng tất cả các lỗi bắt đầu bằng 'invalid_' trong báo cáo chất lượng
    invalid_rows_sum = quality_report.loc[quality_report['check_name'].str.startswith('invalid_'), 'value'].sum()
    # Nếu tham số --fail-on-invalid được bật và phát hiện lỗi dữ liệu bẩn
    if args.fail_on_invalid and invalid_rows_sum > 0:
        print("\n[LỖI] Phát hiện dữ liệu không hợp lệ (Fail-fast policy):")
        # In ra các lỗi cụ thể để kiểm tra
        print(quality_report[quality_report['check_name'].str.startswith('invalid_')])
        # Thoát chương trình với mã lỗi 1 để dừng pipeline ngay lập tức
        sys.exit(1)

    # Bước 6: Phân nhóm độ tuổi thành các khoảng 10 năm cho phân tích MapReduce
    df = add_age_group(df)
    # Bước 7: Thêm cột nhãn số level_encoded (Low=0, Medium=1, High=2) cho huấn luyện ML
    df = add_encoded_label(df)

    df_hdfs, df_ml = build_output_frames(df)

    df_hdfs.to_csv(HDFS_OUTPUT, index=False, encoding="utf-8-sig")
    df_ml.to_csv(ML_OUTPUT, index=False, encoding="utf-8-sig")
    quality_report.to_csv(QUALITY_OUTPUT, index=False, encoding="utf-8-sig")

    print_statistical_verification(df)
    print("\nExported files:")
    print(f"- {HDFS_OUTPUT}")
    print(f"- {ML_OUTPUT}")
    print(f"- {QUALITY_OUTPUT}")

if __name__ == "__main__":
    main()
