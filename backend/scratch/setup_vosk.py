import os
import zipfile
import requests
from tqdm import tqdm

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-tr-0.22.zip"
MODEL_DIR = "models"
MODEL_NAME = "vosk-model-small-tr-0.22"
TARGET_PATH = os.path.join(MODEL_DIR, "vosk-tr")

def download_model():
    if os.path.exists(TARGET_PATH):
        print(f"Model zaten mevcut: {TARGET_PATH}")
        return

    os.makedirs(MODEL_DIR, exist_ok=True)
    zip_path = os.path.join(MODEL_DIR, "model.zip")

    print(f"Model indiriliyor: {MODEL_URL}")
    response = requests.get(MODEL_URL, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(zip_path, 'wb') as f, tqdm(
        total=total_size, unit='iB', unit_scale=True, desc="İndiriliyor"
    ) as pbar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            pbar.update(size)

    print("Zip dosyası ayıklanıyor...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(MODEL_DIR)

    # Klasör ismini sadeleştir
    extracted_path = os.path.join(MODEL_DIR, MODEL_NAME)
    if os.path.exists(extracted_path):
        os.rename(extracted_path, TARGET_PATH)

    os.remove(zip_path)
    print(f"Model başarıyla kuruldu: {TARGET_PATH}")

if __name__ == "__main__":
    download_model()
