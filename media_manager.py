import hashlib
from pathlib import Path
from typing import Optional
import requests
import config

class MediaManager:
    @staticmethod
    def download_product_image(image_url: str) -> Optional[Path]:
        """
        Baixa a imagem real do produto para a pasta de cache local.
        Retorna o caminho absoluto do arquivo para ser anexado no WhatsApp.
        """
        if not image_url or not image_url.startswith("http"):
            return None

        try:
            # Gera nome único baseado no hash da URL
            url_hash = hashlib.md5(image_url.encode("utf-8")).hexdigest()[:12]
            
            # Detecta extensão
            ext = ".jpg"
            if ".webp" in image_url.lower():
                ext = ".webp"
            elif ".png" in image_url.lower():
                ext = ".png"

            dest_path = config.MEDIA_CACHE_DIR / f"deal_{url_hash}{ext}"

            # Se já foi baixada anteriormente, reutiliza
            if dest_path.exists() and dest_path.stat().st_size > 1024:
                return dest_path

            headers = {
                "User-Agent": config.USER_AGENTS[0],
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": "https://www.mercadolivre.com.br/"
            }

            response = requests.get(image_url, headers=headers, timeout=15)
            if response.status_code == 200 and len(response.content) > 500:
                with open(dest_path, "wb") as f:
                    f.write(response.content)
                return dest_path

        except Exception as e:
            print(f"    [Media] Não foi possível baixar imagem de {image_url[:50]}...: {e}")

        return None
