import anthropic
import json
import time
import pandas as pd
from tqdm import tqdm

# ============================================================
# 1. CONFIGURE CLIENT
# ============================================================
# Set your API key here OR use environment variable ANTHROPIC_API_KEY
# Recommended: export ANTHROPIC_API_KEY="sk-ant-..." in your terminal
#              and leave api_key out of the client constructor

client = anthropic.Anthropic(
    api_key="sk-ant-YOUR_API_KEY_HERE"  # Replace with your key
    # OR remove this line and set env var: export ANTHROPIC_API_KEY="sk-ant-..."
)

# ============================================================
# 2. SYSTEM PROMPT (Expert Persona - set once, reused for all rows)
# ============================================================
SYSTEM_PROMPT = """You are an expert Indian Customs Classification Officer with 20 years of experience 
in the Indian Customs Act 1962, the Customs Tariff Act 1975, and all notifications issued by CBIC.
 
You strictly apply:
- General Rules of Interpretation (GIR) Rules 1 through 6
- Relevant Section Notes and Chapter Notes
- CBIC clarifications and court precedents where applicable
 
You always respond with valid JSON only. No explanations, no markdown, no preamble."""


# ============================================================
# 3. SINGLE ITEM CLASSIFICATION FUNCTION
# ============================================================
def classify_item(item_description: str, max_retries: int = 5) -> dict:
    """
    Classify a single product description using Claude.
    Returns dict with keys: cth, bcd_rate, confidence, reasoning
    """
    if not item_description or str(item_description).strip() == "":
        return {
            "cth": None,
            "bcd_rate": None,
            "confidence": None,
            "reasoning": "Empty description",
        }

    prompt = f"""Classify the following product under the Indian Customs Tariff Act, 1975.
 
PRODUCT DESCRIPTION: "{item_description}"
 
Instructions:
1. Apply GIR Rules (especially Rule 1, 2a, 3b) for classification
2. Consider Section Notes and Chapter Notes
3. Analyze material composition, primary function, and specific use
4. Provide the exact 8-digit CTH — never hypothetical codes
5. BCD rate must be the current Standard Rate for this CTH
 
Respond ONLY with this JSON structure:
{{
  "cth": "12345678",
  "bcd_rate": "10%",
  "confidence": "high",
  "reasoning": "Brief one-line reason for this classification"
}}
 
Confidence must be: "high", "medium", or "low"."""

    delay = 2
    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-5",  # Best balance of speed + accuracy
                max_tokens=300,  # JSON response is short
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            raw_text = message.content[0].text.strip()

            # Clean markdown fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            # Parse JSON
            data = json.loads(raw_text)

            return {
                "cth": str(data.get("cth", "")).strip(),
                "bcd_rate": str(data.get("bcd_rate", "")).strip(),
                "confidence": str(data.get("confidence", "")).strip(),
                "reasoning": str(data.get("reasoning", "")).strip(),
            }

        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON parse error on attempt {attempt + 1}: {e}")
            print(f"  Raw response: {raw_text[:200]}")
        except anthropic.RateLimitError:
            print(f"  ⏳ Rate limit hit. Waiting {delay}s before retry...")
        except anthropic.APIStatusError as e:
            print(f"  ❌ API error {e.status_code}: {e.message}")
        except Exception as e:
            print(f"  ❌ Unexpected error on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            time.sleep(delay)
            delay = min(delay * 2, 60)  # Exponential backoff, max 60s

    return {
        "cth": "Error",
        "bcd_rate": "Error",
        "confidence": "Error",
        "reasoning": "All retries failed",
    }


# ============================================================
# 4. BATCH PROCESSING FROM EXCEL
# ============================================================
def classify_excel(
    input_file: str, item_col: str = "Item Desc", nrows: int = None
) -> pd.DataFrame:
    """
    Load an Excel file, classify all items, and return the enriched DataFrame.

    Args:
        input_file: Path to the Excel file
        item_col:   Column name containing product descriptions
        nrows:      Limit rows for testing (None = process all)
    """
    print(f"\n📂 Loading: {input_file}")
    df = pd.read_excel(input_file, nrows=nrows)
    df.columns = df.columns.str.strip()  # Clean column headers

    # Validate column exists
    if item_col not in df.columns:
        raise ValueError(
            f"Column '{item_col}' not found.\n" f"Available columns: {list(df.columns)}"
        )

    print(f"✅ Loaded {len(df)} rows. Starting classification...\n")

    # Add output columns
    df["Correct CTH"] = ""
    df["New BCD Rate"] = ""
    df["Confidence"] = ""
    df["AI Reasoning"] = ""

    # Process each row with progress bar
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Classifying"):
        item_desc = row[item_col]

        result = classify_item(str(item_desc))

        df.at[index, "Correct CTH"] = result["cth"]
        df.at[index, "New BCD Rate"] = result["bcd_rate"]
        df.at[index, "Confidence"] = result["confidence"]
        df.at[index, "AI Reasoning"] = result["reasoning"]

        time.sleep(1)  # Respect rate limits (adjust based on your tier)

    return df


# ============================================================
# 5. QUICK TEST — Single item
# ============================================================
def quick_test():
    """Run a quick test with a few sample products."""
    print("🔍 Running quick test...\n")

    test_items = [
        "Stainless steel kitchen knife with wooden handle",
        "Cotton T-shirt for men, 100% cotton",
        "LED television set 55 inch with HDMI ports",
        "Crude palm oil for edible purposes",
    ]

    for item in test_items:
        print(f"Item: {item}")
        result = classify_item(item)
        print(f"  CTH: {result['cth']}")
        print(f"  BCD: {result['bcd_rate']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Reasoning: {result['reasoning']}\n")


# ============================================================
# 6. MAIN — Run classification on your Excel file
# ============================================================
if __name__ == "__main__":

    # --- Option A: Quick test with sample items ---
    quick_test()

    # --- Option B: Process your Excel file ---
    # Uncomment and update the filename below:

    # INPUT_FILE  = "your_products.xlsx"
    # OUTPUT_FILE = "classified_output.xlsx"
    # ITEM_COLUMN = "Item Desc"           # Your column name
    # TEST_ROWS   = 10                    # Set None to process all rows

    # df_result = classify_excel(
    #     input_file=INPUT_FILE,
    #     item_col=ITEM_COLUMN,
    #     nrows=TEST_ROWS
    # )

    # df_result.to_excel(OUTPUT_FILE, index=False)
    # print(f"\n✅ Done! Output saved to: {OUTPUT_FILE}")
