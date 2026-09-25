# -*- coding: utf-8 -*-
"""Painel local para configurar perfis e executar o PromoPet Hunter."""
import html
import json
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
PROFILES_FILE = BASE_DIR / "perfis.json"
PORT = 8765


def read_data():
    return json.loads(PROFILES_FILE.read_text(encoding="utf-8"))


def write_data(data):
    PROFILES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def field(values, name, default=""):
    return values.get(name, [default])[0].strip()


def category_text(categories):
    return "\n".join(f"{name}: {', '.join(terms)}" for name, terms in categories.items())


def parse_categories(text):
    result = {}
    for line in text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        name, terms = line.split(":", 1)
        values = [term.strip() for term in terms.split(",") if term.strip()]
        if name.strip() and values:
            result[name.strip()] = values
    return result


def esc(value):
    return html.escape(str(value or ""), quote=True)


def page(message=""):
    data = read_data()
    active = data.get("active_profile", "")
    profiles = data.setdefault("profiles", {})
    profile = profiles.get(active, next(iter(profiles.values()), {}))
    categories = profile.get("categories", {})
    return f"""<!doctype html>
<html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>PromoPet Hunter</title><style>
:root{{--ink:#17211b;--muted:#647067;--paper:#f5f4ef;--card:#fff;--green:#245b45;--orange:#d97842;--line:#d9ded7}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:15px Georgia,serif}}
main{{max-width:1080px;margin:0 auto;padding:40px 24px}} header{{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:30px}}
h1{{font-size:42px;line-height:1;margin:0;letter-spacing:0}} .eyebrow{{color:var(--orange);font:700 12px Arial,sans-serif;letter-spacing:1px;text-transform:uppercase}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} section{{background:var(--card);border:1px solid var(--line);padding:22px;border-radius:6px}} h2{{font-size:22px;margin:0 0 16px}} label{{display:block;margin:12px 0 6px;font:700 12px Arial,sans-serif;text-transform:uppercase;color:var(--muted)}} input,textarea,select{{width:100%;border:1px solid var(--line);padding:11px;border-radius:4px;font:15px Arial,sans-serif;background:#fff;color:var(--ink)}} textarea{{min-height:210px;resize:vertical}} .wide{{grid-column:1/-1}} .actions{{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}} button{{border:0;border-radius:4px;padding:12px 16px;background:var(--green);color:white;font-weight:700;cursor:pointer}} button.secondary{{background:#e5ebe5;color:var(--green)}} button.warn{{background:var(--orange)}} .notice{{padding:12px;background:#e9f1e8;border-left:4px solid var(--green);margin-bottom:18px;font:14px Arial,sans-serif}} small{{color:var(--muted);font:13px Arial,sans-serif;line-height:1.45}} @media(max-width:760px){{.grid{{grid-template-columns:1fr}}h1{{font-size:34px}}}}
</style></head><body><main><header><div><div class='eyebrow'>Painel local</div><h1>PromoPet Hunter</h1><small>Perfis por tema, grupo e afiliado sem editar o código.</small></div><div class='eyebrow'>ML + Amazon</div></header>
{f"<div class='notice'>{esc(message)}</div>" if message else ""}
<form method='post' action='/save'><div class='grid'><section><h2>Perfil e destino</h2><label>Perfil ativo</label><select name='profile'>""" + "".join(f"<option value='{esc(name)}' {'selected' if name == active else ''}>{esc(item.get('label', name))}</option>" for name, item in profiles.items()) + f"""</select><label>ID do perfil</label><input name='profile_id' value='{esc(active)}'><small>Use o seletor para editar ou informe um novo ID para criar outro tema.</small><label>Nome exibido</label><input name='label' value='{esc(profile.get('label'))}'><label>Grupo WhatsApp</label><input name='whatsapp_group' value='{esc(profile.get('whatsapp_group'))}'></section>
<section><h2>Links de afiliado</h2><label>Amazon tag</label><input name='amazon_tag' value='{esc(profile.get('affiliate', {}).get('amazon_tag'))}'><label>Mercado Livre matt_tool</label><input name='meli_matt_tool' value='{esc(profile.get('affiliate', {}).get('meli_matt_tool'))}'><label>Mercado Livre matt_word</label><input name='meli_matt_word' value='{esc(profile.get('affiliate', {}).get('meli_matt_word'))}'><small>Esses valores ficam no perfil e podem ser trocados sem editar Python.</small></section>
<section><h2>Mercado Livre</h2><label>Categorias e consultas</label><textarea name='mercadolivre_categories'>{esc(category_text(categories.get('mercadolivre', {})))}</textarea><small>Uma linha por categoria: <b>nome_da_categoria: busca 1, busca 2</b></small></section>
<section><h2>Amazon</h2><label>Categorias e consultas</label><textarea name='amazon_categories'>{esc(category_text(categories.get('amazon', {})))}</textarea><small>Use termos específicos do seu novo tema, como cosméticos pet ou ferramentas.</small></section></div><div class='actions'><button type='submit'>Salvar perfil ativo</button></form>
<form method='post' action='/run' class='actions'><button class='secondary' name='mode' value='test'>Testar 1 oferta no meu número</button><button class='warn' name='mode' value='production'>Iniciar produção</button></form></div></main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def send_html(self, content):
        raw = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.send_html(page())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        values = parse_qs(self.rfile.read(length).decode("utf-8"))
        data = read_data()
        profiles = data.setdefault("profiles", {})
        selected = field(values, "profile_id", field(values, "profile", data.get("active_profile", "banho_tosa")))
        profile = profiles.setdefault(selected, {"label": selected, "categories": {}})
        if self.path == "/save":
            profile["label"] = field(values, "label", selected)
            profile["whatsapp_group"] = field(values, "whatsapp_group")
            profile["clean_old"] = "clean_old" in values
            profile["affiliate"] = {
                "amazon_tag": field(values, "amazon_tag"),
                "meli_matt_tool": field(values, "meli_matt_tool"),
                "meli_matt_word": field(values, "meli_matt_word"),
            }
            profile["categories"] = {
                "mercadolivre": parse_categories(field(values, "mercadolivre_categories")),
                "amazon": parse_categories(field(values, "amazon_categories")),
            }
            data["active_profile"] = selected
            write_data(data)
            self.send_html(page("Perfil salvo. As próximas buscas usarão essas categorias e links."))
            return
        if self.path == "/run":
            mode = field(values, "mode")
            command = [sys.executable, str(BASE_DIR / "bot.py")]
            if mode == "test":
                command.append("--test")
            threading.Thread(target=subprocess.run, args=(command,), kwargs={"cwd": BASE_DIR}, daemon=True).start()
            self.send_html(page("Comando iniciado no terminal. Esta página pode continuar aberta."))
            return
        self.send_html(page("Ação desconhecida."))

    def log_message(self, *_):
        return


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"[*] Painel PromoPet Hunter: {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Painel encerrado.")
        server.server_close()


if __name__ == "__main__":
    main()
