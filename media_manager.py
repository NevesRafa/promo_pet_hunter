import hashlib
from io import BytesIO
import urllib.parse
from pathlib import Path
from typing import Optional
import requests
import config

try:
    from PIL import Image
except ImportError:
    Image = None

class MediaManager:
    @staticmethod
    def _cached_image(url_hash: str) -> Optional[Path]:
        for path in config.MEDIA_CACHE_DIR.glob(f"deal_{url_hash}.*"):
            if not path.is_file() or path.stat().st_size <= 1024:
                continue
            if Image is not None:
                try:
                    with Image.open(path) as image:
                        image.verify()
                    return path
                except Exception:
                    continue
            header = path.read_bytes()[:12]
            if header.startswith((b"\xff\xd8\xff", b"RIFF", b"\x89PNG\r\n\x1a\n")):
                return path
        return None

    @staticmethod
    def _save_image(content: bytes, url_hash: str) -> Optional[Path]:
        """Valida o payload e salva em um formato que o WhatsApp consiga abrir."""
        if Image is not None:
            try:
                with Image.open(BytesIO(content)) as image:
                    image.load()
                    if image.mode in ("RGBA", "LA", "P"):
                        background = Image.new("RGB", image.size, "white")
                        if image.mode == "P":
                            image = image.convert("RGBA")
                        background.paste(image, mask=image.getchannel("A"))
                        image = background
                    else:
                        image = image.convert("RGB")
                    dest_path = config.MEDIA_CACHE_DIR / f"deal_{url_hash}.jpg"
                    image.save(dest_path, format="JPEG", quality=92, optimize=True)
                    return dest_path
            except Exception:
                return None

        signatures = (
            (b"\xff\xd8\xff", ".jpg"),
            (b"RIFF", ".webp"),
            (b"\x89PNG\r\n\x1a\n", ".png"),
            (b"\x00\x00\x00", ".avif"),
        )
        extension = next((ext for signature, ext in signatures if content.startswith(signature)), None)
        if not extension:
            return None
        dest_path = config.MEDIA_CACHE_DIR / f"deal_{url_hash}{extension}"
        dest_path.write_bytes(content)
        return dest_path

    @staticmethod
    def download_product_image(image_url: str) -> Optional[Path]:
        """
        Baixa a imagem real do produto para a pasta de cache local.
        Retorna o caminho absoluto do arquivo para ser anexado no WhatsApp,
        ou None se não conseguir (e AVISA o motivo — antes falhava calado).
        """
        if not image_url or not image_url.startswith("http"):
            return None

        try:
            # Gera nome único baseado no hash da URL
            url_hash = hashlib.md5(image_url.encode("utf-8")).hexdigest()[:12]

            # Se já foi baixada anteriormente, reutiliza
            cached = MediaManager._cached_image(url_hash)
            if cached:
                return cached

            # O Referer precisa combinar com o site de origem da imagem — usar
            # sempre o do Mercado Livre (mesmo pra imagem da Amazon) fazia a
            # Amazon recusar o download silenciosamente em alguns casos.
            dominio_imagem = urllib.parse.urlparse(image_url).netloc.lower()
            if "amazon" in dominio_imagem or "media-amazon" in dominio_imagem or "ssl-images-amazon" in dominio_imagem:
                referer = "https://www.amazon.com.br/"
            elif "mercadolivre" in dominio_imagem or "mlstatic" in dominio_imagem:
                referer = "https://www.mercadolivre.com.br/"
            else:
                referer = None

            headers = {
                "User-Agent": config.USER_AGENTS[0],
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            }
            if referer:
                headers["Referer"] = referer

            response = requests.get(image_url, headers=headers, timeout=15)

            if response.status_code == 200 and len(response.content) > 500:
                saved = MediaManager._save_image(response.content, url_hash)
                if saved:
                    return saved

            # Antes, chegar aqui significava falhar CALADO. Agora avisa o motivo.
            print(
                f"    [Media] Download recusado (HTTP {response.status_code}, "
                f"{len(response.content)} bytes) para {image_url[:60]}..."
            )

            # Segunda tentativa: às vezes o Referer é justamente o que causa a
            # recusa (CDN mais restritivo) — tenta de novo sem ele.
            if referer:
                retry = requests.get(
                    image_url,
                    headers={k: v for k, v in headers.items() if k != "Referer"},
                    timeout=15
                )
                if retry.status_code == 200 and len(retry.content) > 500:
                    saved = MediaManager._save_image(retry.content, url_hash)
                    if saved:
                        print("    [Media] Funcionou na 2ª tentativa (sem Referer).")
                        return saved
                print(f"    [Media] 2ª tentativa também falhou (HTTP {retry.status_code}).")

        except Exception as e:
            print(f"    [Media] Não foi possível baixar imagem de {image_url[:50]}...: {e}")

        return None
