from pathlib import Path

import pandas as pd


DATA_PATH = Path(r"D:\1BigDataproject1\cancer patient data sets.xlsx")
OUTPUT_DIR = Path(r"D:\1BigDataproject1\cleandata cancer")

RAW_TO_CLEAN_COLUMNS = {
    "Patient Id": "patient_id",
    "Age": "age",
    "Gender": "gender",
    "Air Pollution": "air_pollution",
    "Alcohol use": "alcohol_use",
    "Dust Allergy": "dust_allergy",
    "OccuPational Hazards": "occupational_hazards",
    "Genetic Risk": "genetic_risk",
    "chronic Lung Disease": "chronic_lung_disease",
    "Balanced Diet": "balanced_diet",
    "Obesity": "obesity",
    "Smoking": "smoking",
    "Passive Smoker": "passive_smoker",
    "Chest Pain": "chest_pain",
    "Coughing of Blood": "coughing_of_blood",
    "Fatigue": "fatigue",
    "Weight Loss": "weight_loss",
    "Shortness of Breath": "shortness_of_breath",
    "Wheezing": "wheezing",
    "Swallowing Difficulty": "swallowing_difficulty",
    "Clubbing of Finger Nails": "clubbing_of_finger_nails",
    "Frequent Cold": "frequent_cold",
    "Dry Cough": "dry_cough",
    "Snoring": "snoring",
    "Level": "level",
}

IDENTIFICATION_COLUMNS = ["patient_id"]
DEMOGRAPHIC_COLUMNS = ["age", "gender"]
ENVIRONMENTAL_RISK_COLUMNS = [
    "air_pollution",
    "dust_allergy",
    "occupational_hazards",
]
LIFESTYLE_COLUMNS = [
    "alcohol_use",
    "smoking",
    "passive_smoker",
    "balanced_diet",
    "obesity",
]
GENETIC_MEDICAL_COLUMNS = ["genetic_risk", "chronic_lung_disease"]
CLINICAL_SYMPTOM_COLUMNS = [
    "chest_pain",
    "coughing_of_blood",
    "fatigue",
    "weight_loss",
    "shortness_of_breath",
    "wheezing",
    "swallowing_difficulty",
    "clubbing_of_finger_nails",
    "frequent_cold",
    "dry_cough",
    "snoring",
]
TARGET_COLUMNS = ["level"]

NUMERIC_FEATURE_COLUMNS = [
    "age",
    "gender",
    "air_pollution",
    "alcohol_use",
    "dust_allergy",
    "occupational_hazards",
    "genetic_risk",
    "chronic_lung_disease",
    "balanced_diet",
    "obesity",
    "smoking",
    "passive_smoker",
    "chest_pain",
    "coughing_of_blood",
    "fatigue",
    "weight_loss",
    "shortness_of_breath",
    "wheezing",
    "swallowing_difficulty",
    "clubbing_of_finger_nails",
    "frequent_cold",
    "dry_cough",
    "snoring",
]
RISK_SCALE_COLUMNS = [
    column for column in NUMERIC_FEATURE_COLUMNS if column not in {"age", "gender"}
]
VALID_LEVELS = ["Low", "Medium", "High"]
LEVEL_ENCODING = {"Low": 0, "Medium": 1, "High": 2}

HDFS_OUTPUT = OUTPUT_DIR / "cancer_patients_clean_hdfs.csv"
ML_OUTPUT = OUTPUT_DIR / "cancer_patients_ml_ready.csv"
QUALITY_OUTPUT = OUTPUT_DIR / "cancer_cleaning_quality_report.csv"


def load_source_dataset(data_path: Path = DATA_PATH) -> pd.DataFrame:
    """Load the raw Excel dataset and validate the expected source schema."""
    df_raw = pd.read_excel(data_path)
    expected_columns = list(RAW_TO_CLEAN_COLUMNS)
    missing_columns = [column for column in expected_columns if column not in df_raw.columns]
    unexpected_columns = [column for column in df_raw.columns if column not in expected_columns]

    if missing_columns or unexpected_columns:
        raise ValueError(
            "Source schema mismatch. "
            f"Missing columns: {missing_columns}. "
            f"Unexpected columns: {unexpected_columns}."
        )

    return df_raw[expected_columns].copy()


def standardize_schema(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Rename raw Excel columns to stable snake_case pipeline fields."""
    return df_raw.rename(columns=RAW_TO_CLEAN_COLUMNS).copy()


def clean_text_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Clean identifiers and categorical target labels without dropping rows."""
    cleaned = df.copy()
    cleaned["patient_id"] = cleaned["patient_id"].astype(str).str.strip()
    cleaned["level"] = cleaned["level"].astype(str).str.strip().str.title()
    return cleaned


def cast_numeric_features(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce all numeric feature columns to numeric values for validation and ML."""
    casted = df.copy()
    for column in NUMERIC_FEATURE_COLUMNS:
        casted[column] = pd.to_numeric(casted[column], errors="coerce")
    return casted


def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Build the data quality execution log required by the pipeline report."""
    invalid_risk_scale = sum(
        (~df[column].between(1, 9)).sum() for column in RISK_SCALE_COLUMNS
    )
    checks = [
        (
            "invalid_gender",
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
            int((~df["level"].isin(VALID_LEVELS)).sum()),
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


def run_pipeline() -> dict[str, Path]:
    """Execute the full Excel-to-CSV preprocessing pipeline."""
    pd.set_option("display.max_columns", 80)
    pd.set_option("display.width", 160)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_source_dataset()
    df = standardize_schema(df)
    df = clean_text_fields(df)
    df = cast_numeric_features(df)
    quality_report = build_quality_report(df)
    df = add_age_group(df)
    df = add_encoded_label(df)

    df_hdfs, df_ml = build_output_frames(df)

    df_hdfs.to_csv(HDFS_OUTPUT, index=False, encoding="utf-8-sig")
    df_ml.to_csv(ML_OUTPUT, index=False, encoding="utf-8-sig")
    quality_report.to_csv(QUALITY_OUTPUT, index=False, encoding="utf-8-sig")

    print_statistical_verification(df)
    print("\nExported files:")
    for path in [HDFS_OUTPUT, ML_OUTPUT, QUALITY_OUTPUT]:
        print(path)

    return {
        "hdfs": HDFS_OUTPUT,
        "ml_ready": ML_OUTPUT,
        "quality_report": QUALITY_OUTPUT,
    }


if __name__ == "__main__":
    run_pipeline()
