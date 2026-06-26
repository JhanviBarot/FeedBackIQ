import pandas as pd
import io


SUPPORTED_REVIEW_COLUMN_NAMES = [
    "review",
    "reviews",
    "review_text",
    "text",
    "comment",
    "comments",
    "feedback",
    "description",
    "content",
    "message",
]

MAX_FILE_SIZE_MB = 10
MAX_ROWS = 2000


def detect_review_column(columns: list) -> str | None:
    lower_map = {col.lower().strip(): col for col in columns}

    for candidate in SUPPORTED_REVIEW_COLUMN_NAMES:
        if candidate in lower_map:
            return lower_map[candidate]

    for col in columns:
        if any(
            keyword in col.lower()
            for keyword in ["review", "feedback", "comment", "text"]
        ):
            return col

    return None


def parse_uploaded_file(file_obj, filename: str) -> dict:
    try:
        file_obj.seek(0, io.SEEK_END)
        size_mb = file_obj.tell() / (1024 * 1024)
        file_obj.seek(0)

        if size_mb > MAX_FILE_SIZE_MB:
            return {
                "error": f"File is {size_mb:.1f}MB. Maximum allowed is {MAX_FILE_SIZE_MB}MB.",
                "columns": [],
                "dataframe": None,
                "raw_text_lines": [],
            }

        if filename.lower().endswith(".csv"):
            df = pd.read_csv(file_obj)
        elif filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_obj)
        else:
            return {
                "error": "Unsupported file type. Please upload a .csv or .xlsx file.",
                "columns": [],
                "dataframe": None,
                "raw_text_lines": [],
            }

    except Exception as e:
        return {
            "error": f"Could not read file: {str(e)}",
            "columns": [],
            "dataframe": None,
            "raw_text_lines": [],
        }

    if df.empty or len(df.columns) == 0:
        return {
            "error": "The uploaded file is empty or has no columns.",
            "columns": [],
            "dataframe": None,
            "raw_text_lines": [],
        }

    if len(df) > MAX_ROWS:
        df = df.head(MAX_ROWS)

    detected_column = detect_review_column(df.columns.tolist())
    raw_text_lines = []

    if detected_column:
        extraction = extract_review_lines(df, detected_column)
        if extraction["error"] is None:
            raw_text_lines = extraction["raw_text_lines"]

    return {
        "error": None,
        "columns": df.columns.tolist(),
        "dataframe": df,
        "detected_column": detected_column,
        "raw_text_lines": raw_text_lines,
    }


def extract_review_lines(df: pd.DataFrame, review_column: str) -> dict:
    if review_column not in df.columns:
        return {
            "error": f"Column '{review_column}' not found in file.",
            "raw_text_lines": [],
        }

    series = df[review_column].dropna()
    series = series.astype(str).str.strip()
    series = series[series != ""]
    series = series[series.str.lower() != "nan"]

    lines = series.tolist()

    if len(lines) == 0:
        return {
            "error": f"No valid review text found in column '{review_column}'.",
            "raw_text_lines": [],
        }

    return {"error": None, "raw_text_lines": lines}

def lines_to_raw_text(lines: list) -> str:
    return "\n".join(lines)