"""
Extracts the Credit Card Fraud Detection dataset from a local ZIP file.
Since the original Kaggle CSV is 150MB (exceeding GitHub's 100MB limit),
we compress it to a ~65MB ZIP file, commit it, and extract it on Railway startup.
"""
import os
import zipfile

DATA_DIR = "Data"
CSV_PATH = os.path.join(DATA_DIR, "creditcard.csv")
ZIP_PATH = os.path.join(DATA_DIR, "creditcard.zip")

def download_dataset():
    if os.path.exists(CSV_PATH):
        print(f"[DATA] {CSV_PATH} already exists. Skipping extraction.")
        return True
    
    if not os.path.exists(ZIP_PATH):
        print(f"[DATA] ERROR: {ZIP_PATH} not found in the repository!")
        return False
        
    print(f"[DATA] Extracting {ZIP_PATH}...")
    try:
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(DATA_DIR)
            
        if os.path.exists(CSV_PATH):
            size_mb = os.path.getsize(CSV_PATH) / (1024 * 1024)
            print(f"[DATA] Dataset ready: {CSV_PATH} ({size_mb:.1f} MB)")
            return True
        else:
            print("[DATA] ERROR: Extraction succeeded but creditcard.csv not found.")
            return False
            
    except Exception as e:
        print(f"[DATA] Extraction failed: {e}")
        return False

if __name__ == "__main__":
    download_dataset()
