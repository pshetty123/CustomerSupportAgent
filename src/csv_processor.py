import pandas as pd


def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file, skip_blank_lines=False)


def get_text_columns(df: pd.DataFrame) -> list[str]:
    return list(df.columns)


def process_reviews(
    df: pd.DataFrame,
    text_column: str,
    gemini_client,
    progress_callback=None,
) -> tuple[list[dict], int]:
    results = []
    skipped = 0
    total = len(df)

    for i, raw_text in enumerate(df[text_column]):
        text = str(raw_text).strip() if pd.notna(raw_text) else ""

        if not text:
            skipped += 1
            if progress_callback:
                progress_callback(i + 1, total)
            continue

        try:
            analysis = gemini_client.analyze_review(text)
            results.append({
                "original_text": text,
                "sentiment": analysis.sentiment.value,
                "emotion": analysis.emotion.value,
                "category": analysis.category.value,
                "priority": analysis.priority.value,
                "summary": analysis.summary,
                "suggested_reply": analysis.suggested_reply,
            })
        except Exception:
            results.append({
                "original_text": text,
                "sentiment": "ERROR",
                "emotion": "ERROR",
                "category": "ERROR",
                "priority": "ERROR",
                "summary": "Analysis failed after retries.",
                "suggested_reply": "",
            })

        if progress_callback:
            progress_callback(i + 1, total)

    return results, skipped
