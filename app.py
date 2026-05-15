import json
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory, make_response, abort
from dotenv import load_dotenv

import investigations as inv_db
import presets as preset_db
import seeds as seed_db
from llm_utils import get_model_choices
from llm import get_llm, refine_query, filter_results, generate_summary, PRESET_PROMPTS
from search import get_search_results
from scrape import scrape_multiple
from health import check_llm_health, check_search_engines, check_tor_proxy
from export import generate_pdf
from obscura_config import (
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    GOOGLE_API_KEY,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OLLAMA_BASE_URL,
    LLAMA_CPP_BASE_URL,
)
import threading
from crawler import crawl_sources, probe_tier

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")
logging.basicConfig(level=logging.INFO)


def _env_is_set(value):
    return bool(value and str(value).strip() and not str(value).strip().startswith("your_"))


def _get_provider_status():
    providers = []
    for name, value, is_cloud in [
        ("OpenAI", OPENAI_API_KEY, True),
        ("Anthropic", ANTHROPIC_API_KEY, True),
        ("Google", GOOGLE_API_KEY, True),
        ("OpenRouter", OPENROUTER_API_KEY, True),
        ("Ollama", OLLAMA_BASE_URL, False),
        ("llama.cpp", LLAMA_CPP_BASE_URL, False),
    ]:
        configured = _env_is_set(value)
        if configured:
            providers.append({
                "name": name,
                "message": "configured",
                "statusLabel": "configured",
                "statusLevel": "success",
            })
        elif is_cloud:
            providers.append({
                "name": name,
                "message": "API key not set",
                "statusLabel": "not set",
                "statusLevel": "warning",
            })
        else:
            providers.append({
                "name": name,
                "message": "not configured (optional)",
                "statusLabel": "optional",
                "statusLevel": "neutral",
            })
    return providers


def _get_builtin_presets():
    return [
        {
            "key": "threat_intel",
            "label": "🔍 Dark Web Threat Intel",
            "custom": False,
            "description": "",
            "system_prompt": PRESET_PROMPTS["threat_intel"],
        },
        {
            "key": "ransomware_malware",
            "label": "🦠 Ransomware / Malware Focus",
            "custom": False,
            "description": "",
            "system_prompt": PRESET_PROMPTS["ransomware_malware"],
        },
        {
            "key": "personal_identity",
            "label": "👤 Personal / Identity Investigation",
            "custom": False,
            "description": "",
            "system_prompt": PRESET_PROMPTS["personal_identity"],
        },
        {
            "key": "corporate_espionage",
            "label": "🏢 Corporate Espionage / Data Leaks",
            "custom": False,
            "description": "",
            "system_prompt": PRESET_PROMPTS["corporate_espionage"],
        },
    ]


def _build_preset_response():
    builtins = _get_builtin_presets()
    customs = []
    for cp in preset_db.list_presets():
        customs.append({
            "key": cp["key"],
            "label": f"✨ {cp['name']}",
            "custom": True,
            "description": cp.get("description", ""),
            "system_prompt": cp.get("system_prompt", ""),
            "id": cp["id"],
        })
    return builtins + customs


def _preserve_investigation(inv):
    cleaned = {
        "id": inv.get("id"),
        "timestamp": inv.get("timestamp"),
        "query": inv.get("query"),
        "refined_query": inv.get("refined_query"),
        "model": inv.get("model"),
        "preset": inv.get("preset"),
        "summary": inv.get("summary"),
        "status": inv.get("status"),
        "tags": inv.get("tags"),
        "sources": inv.get("sources") or [],
    }
    return cleaned


@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(Path(__file__).parent, "index.html")


@app.route("/<path:path>", methods=["GET"])
def serve_static(path):
    if Path(path).is_file():
        return send_from_directory(Path(__file__).parent, path)
    return send_from_directory(Path(__file__).parent, "index.html")


@app.route("/api/models", methods=["GET"])
def api_models():
    models = get_model_choices()
    return jsonify({"models": [{"key": m, "label": m} for m in models]})


@app.route("/api/providers", methods=["GET"])
def api_providers():
    return jsonify({"providers": _get_provider_status()})


@app.route("/api/presets", methods=["GET", "POST"])
def api_presets():
    if request.method == "GET":
        return jsonify({"presets": _build_preset_response()})

    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    system_prompt = (data.get("system_prompt") or "").strip()
    description = (data.get("description") or "").strip()
    if not name or not system_prompt:
        return jsonify({"error": "Missing preset name or prompt."}), 400
    try:
        cp = preset_db.create_preset(name, system_prompt, description)
        return jsonify({"preset": {
            "key": cp["key"],
            "label": f"✨ {cp['name']}",
            "custom": True,
            "description": cp.get("description", ""),
            "system_prompt": cp.get("system_prompt", ""),
            "id": cp["id"],
        }})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/presets/<int:preset_id>", methods=["PUT", "DELETE"])
def api_preset_item(preset_id):
    if request.method == "DELETE":
        preset_db.delete_preset(preset_id)
        return jsonify({"deleted": True})

    data = request.get_json(force=True) or {}
    try:
        cp = preset_db.update_preset(
            preset_id,
            name=data.get("name"),
            system_prompt=data.get("system_prompt"),
            description=data.get("description"),
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    if not cp:
        return jsonify({"error": "Preset not found."}), 404
    return jsonify({"preset": {
        "key": cp["key"],
        "label": f"✨ {cp['name']}",
        "custom": True,
        "description": cp.get("description", ""),
        "system_prompt": cp.get("system_prompt", ""),
        "id": cp["id"],
    }})


@app.route("/api/investigations", methods=["GET"])
def api_investigations():
    invs = inv_db.load_all()
    return jsonify({"investigations": [ _preserve_investigation(inv) for inv in invs ], "tags": inv_db.get_all_tags()})


@app.route("/api/investigations/<int:inv_id>", methods=["GET", "DELETE"])
def api_investigation_item(inv_id):
    if request.method == "DELETE":
        inv_db.delete_investigation(inv_id)
        return jsonify({"deleted": True})
    inv = inv_db.load_one(inv_id)
    if not inv:
        return jsonify({"error": "Investigation not found."}), 404
    return jsonify(_preserve_investigation(inv))


@app.route("/api/investigations/<int:inv_id>/metadata", methods=["PUT"])
def api_update_investigation_metadata(inv_id):
    inv = inv_db.load_one(inv_id)
    if not inv:
        return jsonify({"error": "Investigation not found."}), 404
    data = request.get_json(force=True) or {}
    status = data.get("status")
    tags = data.get("tags")
    try:
        if status is not None:
            inv_db.update_status(inv_id, status)
        if tags is not None:
            inv_db.update_tags(inv_id, tags)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    inv = inv_db.load_one(inv_id)
    return jsonify(_preserve_investigation(inv))


@app.route("/api/investigations/<int:inv_id>/resummarize", methods=["POST"])
def api_resummarize_investigation(inv_id):
    inv = inv_db.load_one(inv_id)
    if not inv:
        return jsonify({"error": "Investigation not found."}), 404
    data = request.get_json(force=True) or {}
    # Allow callers to force a full re-scrape/resummarize by setting this flag.
    force_rescrape = bool(data.get("force_rescrape"))
    model = data.get("model") or inv.get("model")
    preset = data.get("preset") or inv.get("preset")
    custom_instructions = data.get("custom_instructions", "")
    system_prompt_override = data.get("system_prompt_override")
    try:
        llm = get_llm(model)
        # Build a 'scraped' mapping using saved seed content where possible.
        # By default we will NOT re-scrape missing sources (avoids crawling).
        # If the caller sets force_rescrape, we'll scrape only the missing ones.
        scraped = {}
        sources = inv.get("sources", []) or []
        missing_sources = []
        for src in sources:
            link = src.get("link")
            try:
                s = seed_db.get_seed_by_url(link)
            except Exception:
                s = None
            if s and s.get("content"):
                scraped[link] = s.get("content")
            else:
                missing_sources.append(src)

        if force_rescrape and missing_sources:
            scraped_missing = scrape_multiple(missing_sources, max_workers=4, max_return_chars=2000)
            for k, v in (scraped_missing or {}).items():
                scraped[k] = v

        # If we have no scraped page content but the investigation already
        # contains a saved 'summary', use that text as the content to
        # re-generate a condensed/refined summary (no network I/O).
        if not scraped and inv.get("summary"):
            # Put the existing summary into the mapping under a synthetic key.
            scraped = {"_existing_summary": inv.get("summary")}
        summary = generate_summary(
            llm,
            inv.get("query", ""),
            scraped,
            preset=preset,
            custom_instructions=custom_instructions,
            system_prompt_override=system_prompt_override,
        )
        # Update the existing investigation with the new summary and mark complete
        inv_db.update_summary(inv_id, summary, refined_query=inv.get("refined_query", ""), model=model, preset_label=preset)
        try:
            inv_db.update_status(inv_id, "complete")
        except Exception:
            # ignore if status value is unexpected for older DBs
            pass
        updated = inv_db.load_one(inv_id)
        return jsonify(_preserve_investigation(updated))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/investigations/<int:inv_id>/deep-crawl", methods=["POST"])
def api_deep_crawl_investigation(inv_id):
    inv = inv_db.load_one(inv_id)
    if not inv:
        return jsonify({"error": "Investigation not found."}), 404
    try:
        tier = probe_tier()
        crawled = crawl_sources(inv.get("sources", []), max_workers=4, tier=tier)
        # Persist crawled source content as seeds when possible.
        for source in inv.get("sources", []):
            if source.get("link") in crawled:
                try:
                    db_seed = seed_db.add_seed(source.get("link"), source.get("title", ""))
                    if db_seed:
                        seed_db.mark_crawled(db_seed["id"], status_code=200, content=crawled[source.get("link")])
                except Exception:
                    pass
        return jsonify(_preserve_investigation(inv))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/seeds", methods=["GET", "POST"])
def api_seeds():
    if request.method == "GET":
        return jsonify({"seeds": seed_db.get_all_seeds()})
    data = request.get_json(force=True) or {}
    url_value = data.get("url")
    if isinstance(url_value, dict):
        url_value = url_value.get("text") or str(url_value)
    if not isinstance(url_value, str):
        return jsonify({"error": "Seed URL must be a valid string."}), 400
    url = url_value.strip()
    name_value = data.get("name")
    if isinstance(name_value, dict):
        name_value = name_value.get("text") or str(name_value)
    name = (name_value or "").strip()
    if not url:
        return jsonify({"error": "URL is required."}), 400
    try:
        seed = seed_db.add_seed(url, name)

        # Kick off a background crawl for the newly added seed so users see
        # crawled/loaded content appear in the Seed Manager without a manual
        # deep-crawl of an investigation.
        def _crawl_and_mark(sid, seed_url, seed_name):
            try:
                # Use the batch crawl function from crawler.py even for single URLs
                results = crawl_sources([{"link": seed_url, "title": seed_name}], max_workers=1)
                text = results.get(seed_url)
                if text:
                    seed_db.mark_crawled(sid, status_code=200, content=text)
                else:
                    # mark crawled with empty content so it won't be repeatedly retried
                    seed_db.mark_crawled(sid, status_code=None, content="")
            except Exception:
                logging.exception("Auto-crawl failed for seed %s", seed_url)

        try:
            sid = seed.get("id") if isinstance(seed, dict) else None
            if sid:
                t = threading.Thread(target=_crawl_and_mark, args=(sid, seed.get("url"), seed.get("name")), daemon=True)
                t.start()

        except Exception:
            logging.exception("Failed to start auto-crawl thread")

        return jsonify({"seed": seed})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/seeds/<int:seed_id>/crawl", methods=["POST"])
def api_crawl_seed(seed_id):
    """Manually trigger a crawl for a specific seed id (useful for debugging)."""
    try:
        seeds = seed_db.get_all_seeds() or []
        seed = next((s for s in seeds if int(s.get("id")) == int(seed_id)), None)
        if not seed:
            return jsonify({"error": "Seed not found."}), 404

        # Run crawl synchronously using crawl_sources and persist result
        results = crawl_sources([{"link": seed.get("url"), "title": seed.get("name", "")}], max_workers=1)
        text = results.get(seed.get("url"))
        if text:
            seed_db.mark_crawled(seed_id, status_code=200, content=text)
        else:
            seed_db.mark_crawled(seed_id, status_code=None, content="")
        return jsonify({"result": {"url": seed.get("url"), "text": text}})
    except Exception as exc:
        logging.exception("Manual seed crawl failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/seeds/<int:seed_id>", methods=["DELETE", "POST"])
def api_delete_seed(seed_id):
    try:
        seed_db.delete_seed(seed_id)
        return jsonify({"deleted": True})
    except Exception as exc:
        logging.exception("Failed to delete seed %s", seed_id)
        return jsonify({"error": str(exc)}), 500


@app.route("/api/health/llm", methods=["POST"])
def api_health_llm():
    data = request.get_json(silent=True) or {}
    model = data.get("model")
    if not model:
        return jsonify({"status": ["Missing model for LLM health check."]}), 400
    result = check_llm_health(model)
    output = [f"{result['provider']} — {result['status']} ({result['latency_ms']}ms)" if result["latency_ms"] is not None else f"{result['provider']} — {result['status']}" ]
    if result.get("error"):
        output.append(f"error: {result['error']}")
    return jsonify({"status": output})


@app.route("/api/health/search", methods=["POST"])
def api_health_search():
    tor_result = check_tor_proxy()
    search_results = check_search_engines()
    output = []
    output.append(f"Tor Proxy — {tor_result['status']} ({tor_result['latency_ms']}ms)" if tor_result['latency_ms'] is not None else f"Tor Proxy — {tor_result['status']}")
    if tor_result.get("error"):
        output.append(f"error: {tor_result['error']}")
    for result in search_results:
        detail = f"{result['name']} — {result['status']} ({result['latency_ms']}ms)" if result.get("latency_ms") is not None else f"{result['name']} — {result['status']}"
        if result.get("error"):
            detail += f" — {result['error']}"
        output.append(detail)
    return jsonify({"status": output})


from flask import Response

@app.route("/api/investigate", methods=["POST"])
def api_investigate():
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Query is required."}), 400

    model = data.get("model")
    if not model:
        return jsonify({"error": "LLM model selection is required."}), 400

    preset = data.get("preset") or "threat_intel"
    threads = int(data.get("threads") or 4)
    max_results = int(data.get("max_results") or 50)
    max_scrape = int(data.get("max_scrape") or 10)
    max_content_chars = int(data.get("max_content_chars") or 2000)

    try:
        llm = get_llm(model)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    def generate():
        try:
            yield f"data: {json.dumps({'status': 'Refining query...'})}\n\n"
            refined = refine_query(llm, query)
            
            yield f"data: {json.dumps({'status': 'Searching dark web for: ' + refined})}\n\n"
            results = get_search_results(refined, max_workers=threads)
            if len(results) > max_results:
                results = results[:max_results]
            
            yield f"data: {json.dumps({'status': f'Filtering {len(results)} results...'})}\n\n"
            filtered = filter_results(llm, refined, results)
            if len(filtered) > max_scrape:
                filtered = filtered[:max_scrape]
            
            yield f"data: {json.dumps({'status': f'Scraping {len(filtered)} selected sources...'})}\n\n"
            scraped = scrape_multiple(filtered, max_workers=threads, max_return_chars=max_content_chars)
            
            yield f"data: {json.dumps({'status': 'Generating final intelligence report...'})}\n\n"
            summary = generate_summary(
                llm,
                query,
                scraped,
                preset=preset,
                custom_instructions="",
                system_prompt_override=None,
            )
            
            inv_id = inv_db.save_investigation(
                query=query,
                refined_query=refined,
                model=model,
                preset_label=preset,
                sources=filtered,
                summary=summary,
                status="complete",
            )
            
            inv = inv_db.load_one(inv_id)
            response = _preserve_investigation(inv)
            response.update({
                "results": results,
                "filtered": filtered,
                "scraped": scraped,
                "done": True
            })
            yield f"data: {json.dumps(response)}\n\n"
        except Exception as exc:
            logging.exception("investigation failed")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route("/api/export/pdf", methods=["POST"])
def api_export_pdf():
    data = request.get_json(force=True) or {}
    pdf_data = data.get("summary")
    metadata = data.get("metadata") or {}
    if not pdf_data:
        return jsonify({"error": "Summary content is required."}), 400
    inv = {
        "query": metadata.get("query", ""),
        "refined_query": metadata.get("refined_query", ""),
        "model": metadata.get("model", ""),
        "preset": metadata.get("preset", ""),
        "status": metadata.get("status", "active"),
        "tags": metadata.get("tags", ""),
        "timestamp": metadata.get("timestamp") or datetime.now().isoformat(),
        "sources": metadata.get("sources", []),
        "summary": pdf_data,
    }
    try:
        pdf_bytes = generate_pdf(inv)
        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename=obscura_investigation_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        return response
    except Exception as exc:
        logging.exception("PDF export failed")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501)
