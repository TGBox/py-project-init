"""Universal AI client for project architecture, language, and template advice."""
from dataclasses import dataclass, field
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

KEYRING_SERVICE = "py-project-init-ai"

PROVIDER_DEFAULTS = {
    "gemini": {
        "name": "Google Gemini",
        "default_model": "gemini-1.5-flash",
        "base_url": "https://generativelanguage.googleapis.com",
        "needs_key": True,
        "env_var": "GEMINI_API_KEY",
    },
    "openai": {
        "name": "OpenAI",
        "default_model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "needs_key": True,
        "env_var": "OPENAI_API_KEY",
    },
    "openrouter": {
        "name": "OpenRouter",
        "default_model": "google/gemini-2.0-flash-exp:free",
        "base_url": "https://openrouter.ai/api/v1",
        "needs_key": True,
        "env_var": "OPENROUTER_API_KEY",
    },
    "ollama": {
        "name": "Ollama (Lokal / Kostenlos)",
        "default_model": "llama3.2",
        "base_url": "http://localhost:11434/v1",
        "needs_key": False,
        "env_var": "",
    },
    "custom": {
        "name": "Benutzerdefiniert (OpenAI-kompatibel)",
        "default_model": "default",
        "base_url": "http://localhost:8000/v1",
        "needs_key": False,
        "env_var": "",
    },
}


class AiAdvisorError(RuntimeError):
    """Raised when an AI API request or response parsing fails."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass
class AiProviderConfig:
    provider: str = "gemini"
    api_key: str = ""
    model: str = "gemini-1.5-flash"
    base_url: str = ""

    def get_effective_base_url(self) -> str:
        if self.base_url.strip():
            return self.base_url.strip().rstrip("/")
        default_info = PROVIDER_DEFAULTS.get(self.provider.lower())
        return default_info["base_url"] if default_info else ""


@dataclass
class AiAdvice:
    recommended_template_id: str
    project_name: str
    description: str
    language: str
    framework: str = ""
    reasoning: str = ""
    architecture_plan: str = ""
    suggested_libraries: list[str] = field(default_factory=list)
    alternatives: list[dict[str, str]] = field(default_factory=list)
    raw_response: str = ""


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return ctx


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        newline_idx = cleaned.find("\n")
        if newline_idx != -1:
            cleaned = cleaned[newline_idx + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as err:
        raise AiAdvisorError(f"Antwort des KI-Modells konnte nicht als JSON interpretiert werden: {err}") from err


def build_system_prompt(available_templates: list[dict[str, Any]]) -> str:
    """Builds a targeted system prompt listing all available templates and expected JSON schema."""
    lines = [
        "Du bist ein erfahrener Software-Architekt und Berater für Softwareprojekte.",
        "Ein Entwickler benötigt deine Entscheidungshilfe, um die beste Programmiersprache, Vorlage,",
        "den Projektnamen und den optimalen Implementierungsweg für ein neues Projekt zu finden.",
        "",
        "Verfügbare Projektvorlagen im System:",
    ]
    for tpl in available_templates:
        tid = tpl.get("id", "")
        name = tpl.get("name", tid)
        lang = tpl.get("language", "Universal")
        desc = tpl.get("description", "")
        lines.append(f"- ID '{tid}': [{lang}] {name} – {desc}")

    lines.extend([
        "",
        "WICHTIGE REGELN:",
        "1. Wähle als 'recommended_template_id' GENAU eine der oben aufgelisteten IDs.",
        "2. 'project_name' muss ein gültiger Kebab-Case Identifier sein (z. B. 'invoice-manager', 'rechnung-cli').",
        "3. Alle Erklärungen und Texte ('description', 'reasoning', 'architecture_plan') MÜSSEN auf Deutsch sein.",
        "4. Antworte AUSSCHLIESSLICH im folgenden gültigen JSON-Format ohne zusätzlichen Text:",
        "{",
        '  "recommended_template_id": "string",',
        '  "project_name": "string",',
        '  "description": "Prägnante 1-Satz Zusammenfassung auf Deutsch",',
        '  "language": "string",',
        '  "framework": "string",',
        '  "reasoning": "Ausführliche Begründung auf Deutsch, warum diese Vorlage/Sprache ideal ist",',
        '  "architecture_plan": "Strukturierter Schritt-für-Schritt Implementierungs- und Architekturplan",',
        '  "suggested_libraries": ["lib1", "lib2"],',
        '  "alternatives": [',
        '    {"template_id": "string", "name": "Name", "tradeoff": "Tradeoff-Erklärung"}',
        "  ]",
        "}",
    ])
    return "\n".join(lines)


def query_ai_advisor(
    user_idea: str,
    available_templates: list[dict[str, Any]],
    config: AiProviderConfig,
    timeout: float = 35.0,
) -> AiAdvice:
    """Sends a project consultation request to the selected AI provider."""
    idea = user_idea.strip()
    if not idea:
        raise AiAdvisorError("Bitte beschreibe zuerst deine Projektidee oder Anforderungen.")

    system_prompt = build_system_prompt(available_templates)
    provider = config.provider.lower().strip()
    base_url = config.get_effective_base_url()
    api_key = config.api_key.strip()

    if config.provider != "ollama" and PROVIDER_DEFAULTS.get(provider, {}).get("needs_key") and not api_key:
        raise AiAdvisorError(
            f"Kein API-Key für Provider '{config.provider}' hinterlegt. "
            f"Bitte API-Key eintragen oder Umgebungsvariable {PROVIDER_DEFAULTS[provider]['env_var']} setzen."
        )

    if provider == "gemini":
        return _query_gemini(user_idea, system_prompt, config, base_url, api_key, timeout)
    else:
        # OpenAI, OpenRouter, Ollama, Custom all share OpenAI chat completion API
        return _query_openai_compatible(user_idea, system_prompt, config, base_url, api_key, timeout)


def _query_gemini(
    user_idea: str,
    system_prompt: str,
    config: AiProviderConfig,
    base_url: str,
    api_key: str,
    timeout: float,
) -> AiAdvice:
    model = config.model.strip() or "gemini-1.5-flash"
    url = f"{base_url}/v1beta/models/{model}:generateContent?key={urllib.parse.quote(api_key)}"

    body_data = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"Projektidee / Anforderungen des Entwicklers:\n{user_idea}"}],
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "responseMimeType": "application/json",
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as res:
            raw = res.read().decode("utf-8")
            data = json.loads(raw)
            candidates = data.get("candidates", [])
            if not candidates:
                raise AiAdvisorError("Gemini hat keine Antwort-Kandidaten zurückgegeben.")
            first_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = _extract_json(first_part)
            return _dict_to_advice(parsed, raw)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            err_data = json.loads(e.read() or b"{}")
            detail = err_data.get("error", {}).get("message", "")
        except Exception:
            pass
        raise AiAdvisorError(f"Google Gemini HTTP {e.code}: {detail or e.reason}", status=e.code) from e
    except urllib.error.URLError as e:
        raise AiAdvisorError(f"Gemini API nicht erreichbar: {e.reason}") from e


def _query_openai_compatible(
    user_idea: str,
    system_prompt: str,
    config: AiProviderConfig,
    base_url: str,
    api_key: str,
    timeout: float,
) -> AiAdvice:
    url = f"{base_url}/chat/completions"
    model = config.model.strip() or "gpt-4o-mini"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Projektidee / Anforderungen des Entwicklers:\n{user_idea}"},
    ]

    body_data: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
    }

    # Only include response_format json_object for providers that support it reliably
    if config.provider in ("openai", "openrouter"):
        body_data["response_format"] = {"type": "json_object"}

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if config.provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/DaniBani/py-project-init"
        headers["X-Title"] = "py-project-init"

    req = urllib.request.Request(
        url,
        data=json.dumps(body_data).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as res:
            raw = res.read().decode("utf-8")
            data = json.loads(raw)
            choices = data.get("choices", [])
            if not choices:
                raise AiAdvisorError("KI-Provider hat keine Antworten zurückgegeben.")
            text = choices[0].get("message", {}).get("content", "")
            parsed = _extract_json(text)
            return _dict_to_advice(parsed, raw)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            err_data = json.loads(e.read() or b"{}")
            detail = err_data.get("error", {}).get("message", "")
        except Exception:
            pass
        raise AiAdvisorError(f"{config.provider.upper()} HTTP {e.code}: {detail or e.reason}", status=e.code) from e
    except urllib.error.URLError as e:
        raise AiAdvisorError(f"{config.provider.upper()} nicht erreichbar ({base_url}): {e.reason}") from e


def _dict_to_advice(data: dict[str, Any], raw_response: str) -> AiAdvice:
    name = (data.get("project_name") or "").strip().lower().replace(" ", "-")
    # Clean up name if it has disallowed chars
    name = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_")).strip("-_")
    if not name:
        name = "my-project"

    return AiAdvice(
        recommended_template_id=str(data.get("recommended_template_id") or "python-cli").strip(),
        project_name=name,
        description=str(data.get("description") or "").strip(),
        language=str(data.get("language") or "").strip(),
        framework=str(data.get("framework") or "").strip(),
        reasoning=str(data.get("reasoning") or "").strip(),
        architecture_plan=str(data.get("architecture_plan") or "").strip(),
        suggested_libraries=list(data.get("suggested_libraries") or []),
        alternatives=list(data.get("alternatives") or []),
        raw_response=raw_response,
    )


# ── Credential Storage via keyring & Environment Variables ───────────────────

def load_ai_key(provider: str) -> str:
    prov = provider.lower().strip()
    try:
        import keyring
        stored = keyring.get_password(KEYRING_SERVICE, prov)
        if stored:
            return stored.strip()
    except Exception:
        pass

    info = PROVIDER_DEFAULTS.get(prov)
    if info and info.get("env_var"):
        env_val = os.environ.get(info["env_var"], "")
        if env_val:
            return env_val.strip()

    return ""


def save_ai_key(provider: str, api_key: str) -> bool:
    prov = provider.lower().strip()
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, prov, api_key.strip())
        return True
    except Exception:
        return False


def delete_ai_key(provider: str) -> None:
    prov = provider.lower().strip()
    try:
        import keyring
        keyring.delete_password(KEYRING_SERVICE, prov)
    except Exception:
        pass
