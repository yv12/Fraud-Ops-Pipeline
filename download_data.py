"""
Downloads the Credit Card Fraud Detection dataset if not present locally.
Used by the auto-initialization on Railway where the CSV isn't in the repo.
"""
import os
import zipfile
import urllib.request

DATA_DIR = "Data"
CSV_PATH = os.path.join(DATA_DIR, "creditcard.csv")

# Public mirror hosted on the OpenML platform (no authentication needed)
DOWNLOAD_URL = "https://github.com/nsethi31/Kaggle-Data-Credit-Card-Fraud-Detection/raw/master/creditcard.csv.zip"

def download_dataset():
    if os.path.exists(CSV_PATH):
        print(f"[DATA] {CSV_PATH} already exists. Skipping download.")
        return True
    
    os.makedirs(DATA_DIR, exist_ok=True)
    zip_path = os.path.join(DATA_DIR, "creditcard.csv.zip")
    
    print(f"[DATA] Downloading credit card fraud dataset...")
    try:
        urllib.request.urlretrieve(DOWNLOAD_URL, zip_path)
        print(f"[DATA] Download complete. Extracting...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(DATA_DIR)
        
        os.remove(zip_path)
        
        if os.path.exists(CSV_PATH):
            size_mb = os.path.getsize(CSV_PATH) / (1024 * 1024)
            print(f"[DATA] Dataset ready: {CSV_PATH} ({size_mb:.1f} MB)")
            return True
        else:
            print("[DATA] ERROR: Extraction succeeded but creditcard.csv not found.")
            return False
            
    except Exception as e:
        print(f"[DATA] Download failed: {e}")
        # Clean up partial download
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return False

if __name__ == "__main__":
    download_dataset()
