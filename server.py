import json
import socket
from pathlib import Path

from aiohttp import web
from sqlalchemy import select

from db import Ad, AsyncSession, Base, engine
from errors import HttpError
from schema import CreateAd, UpdateAd, validate


@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except HttpError as err:
        return web.json_response({"error": err.message}, status=err.status_code)


async def index(request):
    return web.Response(text=HTML, content_type="text/html")


HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Expires" content="0">
<title>Объявления</title>
<style>
body { font-family: Arial, sans-serif; max-width: 700px; margin: 30px auto; padding: 0 20px; }
h1 { margin-bottom: 20px; }
h2 { margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
input, textarea { width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
button { padding: 10px 20px; border: none; border-radius: 4px; color: white; cursor: pointer; }
.btn-create { background: #28a745; }
.btn-get { background: #007bff; }
.btn-delete { background: #dc3545; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
td, th { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { background: #f5f5f5; }
#result { margin-top: 15px; padding: 10px; background: #f0f0f0; border-radius: 4px; white-space: pre-wrap; font-family: monospace; min-height: 30px; }
</style>
</head>
<body>
<h1>Объявления</h1>

<h2>Создать объявление</h2>
<input type="text" id="title" placeholder="Заголовок">
<textarea id="description" placeholder="Описание" rows="3"></textarea>
<input type="text" id="owner" placeholder="Владелец">
<button class="btn-create" onclick="doCreate()">Создать</button>

<h2>Получить объявление по ID</h2>
<input type="number" id="get_id" placeholder="ID">
<button class="btn-get" onclick="doGet()">Получить</button>

<h2>Получить все объявления</h2>
<button class="btn-get" onclick="doList()">Показать все</button>

<h2>Удалить объявление по ID</h2>
<input type="number" id="del_id" placeholder="ID">
<button class="btn-delete" onclick="doDelete()">Удалить</button>

<h2>Результат</h2>
<div id="result"></div>

<script>
(function() {
    var BASE = window.location.origin;

    function show(text) {
        document.getElementById("result").textContent = text;
    }

    window.doCreate = function() {
        var title = document.getElementById("title").value.trim();
        var desc = document.getElementById("description").value.trim();
        var owner = document.getElementById("owner").value.trim();
        if (!title || !owner) {
            show("Заполните заголовок и владельца");
            return;
        }
        var data = {title: title, owner: owner};
        if (desc) data.description = desc;
        fetch(BASE + "/ads", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        })
        .then(function(r) { return r.json().then(function(j) { return {s: r.status, d: j}; }); })
        .then(function(r) { show("Статус: " + r.s + "\n" + JSON.stringify(r.d, null, 2)); })
        .catch(function(e) { show("Ошибка: " + e.message); });
    };

    window.doGet = function() {
        var id = document.getElementById("get_id").value.trim();
        if (!id) { show("Введите ID"); return; }
        fetch(BASE + "/ads/" + id)
        .then(function(r) { return r.json().then(function(j) { return {s: r.status, d: j}; }); })
        .then(function(r) { show("Статус: " + r.s + "\n" + JSON.stringify(r.d, null, 2)); })
        .catch(function(e) { show("Ошибка: " + e.message); });
    };

    window.doList = function() {
        fetch(BASE + "/ads")
        .then(function(r) { return r.json().then(function(j) { return {s: r.status, d: j}; }); })
        .then(function(r) { show("Статус: " + r.s + "\n" + JSON.stringify(r.d, null, 2)); })
        .catch(function(e) { show("Ошибка: " + e.message); });
    };

    window.doDelete = function() {
        var id = document.getElementById("del_id").value.trim();
        if (!id) { show("Введите ID"); return; }
        fetch(BASE + "/ads/" + id, {method: "DELETE"})
        .then(function(r) { return r.json().then(function(j) { return {s: r.status, d: j}; }); })
        .then(function(r) { show("Статус: " + r.s + "\n" + JSON.stringify(r.d, null, 2)); })
        .catch(function(e) { show("Ошибка: " + e.message); });
    };

    console.log("JS OK");
})();
</script>
</body>
</html>"""


async def get_all_ads(request):
    async with AsyncSession() as session:
        result = await session.execute(select(Ad))
        ads = result.scalars().all()
        return web.json_response([ad.dict for ad in ads])


async def create_ad(request):
    try:
        data = await request.json()
    except Exception as exc:
        raise HttpError("no json data", 400) from exc

    if not data:
        raise HttpError("no json data", 400)

    valid_data = validate(data, CreateAd)

    ad = Ad(title=valid_data["title"], owner=valid_data["owner"])
    if valid_data.get("description"):
        ad.description = valid_data["description"]

    async with AsyncSession() as session:
        try:
            session.add(ad)
            await session.commit()
            await session.refresh(ad)
            return web.json_response(ad.dict, status=201)
        except Exception as exc:
            await session.rollback()
            raise HttpError(str(exc), 500) from exc


async def get_ad_detail(request):
    ad_id = int(request.match_info["ad_id"])
    async with AsyncSession() as session:
        ad = await session.get(Ad, ad_id)
        if ad is None:
            raise HttpError("ad not found", 404)
        return web.json_response(ad.dict)


async def update_ad(request):
    ad_id = int(request.match_info["ad_id"])
    async with AsyncSession() as session:
        try:
            ad = await session.get(Ad, ad_id)
            if ad is None:
                raise HttpError("ad not found", 404)

            try:
                payload = await request.json()
            except Exception:
                payload = {}

            if not payload:
                payload = {}

            valid_data = validate(payload, UpdateAd)

            if valid_data.get("title") is not None:
                ad.title = valid_data["title"]
            if valid_data.get("description") is not None:
                ad.description = valid_data["description"]
            if valid_data.get("owner") is not None:
                ad.owner = valid_data["owner"]

            await session.commit()
            await session.refresh(ad)
            return web.json_response(ad.dict)
        except HttpError:
            raise
        except Exception as exc:
            await session.rollback()
            raise HttpError(str(exc), 500) from exc


async def delete_ad(request):
    ad_id = int(request.match_info["ad_id"])
    async with AsyncSession() as session:
        try:
            ad = await session.get(Ad, ad_id)
            if ad is None:
                raise HttpError("ad not found", 404)
            await session.delete(ad)
            await session.commit()
            return web.json_response({"message": "deleted"})
        except HttpError:
            raise
        except Exception as exc:
            await session.rollback()
            raise HttpError(str(exc), 500) from exc


async def on_startup(app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def on_cleanup(app):
    await engine.dispose()


def create_app():
    app = web.Application(middlewares=[error_middleware])
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.router.add_get("/", index)
    app.router.add_get("/ads", get_all_ads)
    app.router.add_post("/ads", create_ad)
    app.router.add_get(r"/ads/{ad_id:\d+}", get_ad_detail)
    app.router.add_patch(r"/ads/{ad_id:\d+}", update_ad)
    app.router.add_delete(r"/ads/{ad_id:\d+}", delete_ad)
    return app


app = create_app()
PORT_FILE = Path(__file__).with_name("server_port.txt")


def get_free_port(start_port=5000, max_tries=10):
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Нет свободных портов в диапазоне 5000-5009")


def write_port_file(port):
    PORT_FILE.write_text(str(port), encoding="utf-8")


if __name__ == "__main__":
    port = get_free_port()
    write_port_file(port)
    print(f"Running on http://0.0.0.0:{port}")
    web.run_app(create_app(), port=port)
