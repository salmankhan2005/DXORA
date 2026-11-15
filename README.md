# Automated Multi-Platform Posting System

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-2.5.3-E92063.svg)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/tests-33%20passed%20%7C%2092%25%20coverage-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

A high-performance, asynchronous Python service built with **FastAPI** that automatically publishes short promotional and marketing messages across multiple third-party social networks, messaging portals, and developer communities via their official REST APIs.

---

## Table of Contents

- [1. System Architecture](#1-system-architecture)
- [2. Platform Research & API Integrations](#2-platform-research--api-integrations)
- [3. API Specification](#3-api-specification)
  - [Endpoint: `POST /posting`](#endpoint-post-posting)
  - [Input Validation Rules](#input-validation-rules)
  - [Example Request & Response](#example-request--response)
- [4. Project Structure](#4-project-structure)
- [5. Installation & Setup](#5-installation--setup)
- [6. Configuration (.env)](#6-configuration-env)
- [7. Running the Application](#7-running-the-application)
- [8. Testing & Code Coverage](#8-testing--code-coverage)
- [9. Fault Isolation & Concurrency](#9-fault-isolation--concurrency)
- [10. Submission Details](#10-submission-details)

---

## 1. System Architecture

The system is designed with an extensible **Adapter / Strategy Pattern**. Every platform implements a common `BasePlatform` abstract interface, and all platforms are executed concurrently using Python's `asyncio.gather(..., return_exceptions=True)`.

```mermaid
flowchart TD
    Client[Client / Caller] -->|POST /posting| Router[FastAPI Router]
    Router -->|Validate Payload| Schemas[Pydantic Validation<br/><= 200 chars, exactly 1 CTA link]
    Schemas -->|Validated Message + CTA| Service[PostingService]
    
    subgraph Concurrency[Concurrent Async Execution (Fault Isolated)]
        Service -->|asyncio.gather| P1[TelegramPlatform]
        Service -->|asyncio.gather| P2[DiscordPlatform]
        Service -->|asyncio.gather| P3[MastodonPlatform]
        Service -->|asyncio.gather| P4[Twitter / X Platform]
        Service -->|asyncio.gather| P5[SlackPlatform]
    end

    P1 -->|POST /sendMessage| TelegramAPI[(Telegram Bot API)]
    P2 -->|POST /webhooks| DiscordAPI[(Discord Webhook API)]
    P3 -->|POST /api/v1/statuses| MastodonAPI[(Mastodon REST API)]
    P4 -->|POST /2/tweets| TwitterAPI[(Twitter / X API v2)]
    P5 -->|POST /chat.postMessage| SlackAPI[(Slack Webhook / Web API)]

    P1 -.-> Aggregator[Results Aggregator]
    P2 -.-> Aggregator
    P3 -.-> Aggregator
    P4 -.-> Aggregator
    P5 -.-> Aggregator

    Aggregator -->|PostingResponse JSON| Client
```

### Key Architectural Highlights
- **Non-Blocking Concurrency**: All platform requests run in parallel. A slow platform or network delay on one API never holds up the execution of others.
- **Total Fault Isolation**: Each platform is wrapped in independent exception boundaries. If one platform fails (e.g. rate limit, bad credentials, network timeout), the remaining platforms continue publishing unimpeded.
- **Simulation Mode**: A configurable mock mode (`SIMULATION_MODE=true`) allows developers and evaluators to test full multi-platform publishing pipelines without requiring live production API tokens.

---

## 2. Platform Research & API Integrations

The service integrates **5 major third-party platforms**:

| Platform | Official API Documentation | Authentication Method | Endpoint Used | Public Access |
|---|---|---|---|---|
| **Telegram** | [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage) | Bot Token (`bot<TOKEN>`) | `POST https://api.telegram.org/bot<TOKEN>/sendMessage` | `true` (if channel username configured), `false` (if private chat) |
| **Discord** | [Discord Webhook Docs](https://discord.com/developers/docs/resources/webhook#execute-webhook) | Webhook URL Token | `POST https://discord.com/api/webhooks/<id>/<token>?wait=true` | `false` (internal channel permissions) |
| **Mastodon** | [Mastodon API v1](https://docs.joinmastodon.org/methods/statuses/#create) | Bearer Token (OAuth2) | `POST https://<instance>/api/v1/statuses` | `true` (public federated timeline) |
| **Twitter / X** | [X API v2 Manage Tweets](https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets) | Bearer Token / OAuth 2.0 User Context | `POST https://api.twitter.com/2/tweets` | `true` (public tweet) |
| **Slack** | [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks) | Webhook URL or Bot Token (`xoxb-`) | `POST <webhook_url>` or `POST https://slack.com/api/chat.postMessage` | `false` (private workspace access) |

---

## 3. API Specification

### Endpoint: `POST /posting`

Publishes a message across all integrated platforms.

#### Headers
```http
Content-Type: application/json
```

#### Request Body
```json
{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

### Input Validation Rules

The input is validated using strict Pydantic v2 schemas:
1. **Character Limit**: Total message length must **not exceed 200 characters**.
2. **CTA Link Presence & Uniqueness**: Message must contain **exactly one CTA link** (0 links or $\ge 2$ links triggers validation failure).
3. **URL Format & Domain Verification**: The link must use `http://` or `https://` protocol with an RFC-compliant domain name or localhost.
4. **Internal Platform Selection**: Platform selection is handled strictly internally; extra payload fields (e.g. `platforms`) are forbidden and rejected with HTTP 422.

#### Example Validation Error Response (HTTP 422)
```json
{
  "success": false,
  "error": "Input validation failed. Please check the requirements.",
  "details": [
    {
      "field": "message",
      "message": "Message must contain exactly one CTA link, but none was found."
    }
  ]
}
```

---

### Example Request & Response

#### Request
```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

#### Response (Simulation Mode / Live Configured)
```json
{
  "success": true,
  "results": [
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/dxora_channel/67159",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:49:19",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "success",
      "posted_url": "https://discord.com/channels/128471928374829102/987654321098765432/1794727159456",
      "public_access": false,
      "date": "2026-11-15",
      "time": "12:49:19",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@dxora_bot/179472716689",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:49:19",
      "error": null
    },
    {
      "platform": "Twitter / X",
      "status": "success",
      "posted_url": "https://x.com/dxora_official/status/1800000001794727159",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:49:19",
      "error": null
    },
    {
      "platform": "Slack",
      "status": "success",
      "posted_url": "https://slack.com/archives/C07DXORA01/p1794727159000100",
      "public_access": false,
      "date": "2026-11-15",
      "time": "12:49:19",
      "error": null
    }
  ]
}
```

---

## 4. Project Structure

```text
automated-posting/
│
├── app/
│   ├── __init__.py                # Package initialization and version definition
│   ├── main.py                    # FastAPI application, exception handlers, and endpoints
│   ├── schemas.py                 # Pydantic v2 models and custom field validators
│   ├── config.py                  # Pydantic Settings configuration loader
│   ├── platforms/
│   │   ├── __init__.py            # Platform registry and adapter discovery
│   │   ├── base.py                # Abstract BasePlatform with error isolation & timing
│   │   ├── telegram.py            # Telegram Bot API integration
│   │   ├── discord.py             # Discord Webhook API integration
│   │   ├── mastodon.py            # Mastodon REST API v1 integration
│   │   ├── twitter.py             # Twitter / X API v2 integration
│   │   └── slack.py               # Slack Webhook / Web API integration
│   └── services/
│       ├── __init__.py
│       └── posting_service.py     # Concurrent asyncio orchestrator
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures and settings overrides
│   ├── test_validation.py         # Unit & API tests for 200 chars limit & CTA link rules
│   ├── test_platforms.py          # Platform unit tests (mocked HTTP & error paths)
│   └── test_posting.py            # End-to-end integration and concurrency tests
│
├── .env.example                   # Environment variable template
├── .gitignore                     # Git ignore rules (prevents credential leaks)
├── pytest.ini                     # Pytest configuration
├── requirements.txt               # Project dependencies
└── README.md                      # Comprehensive documentation
```

---

## 5. Installation & Setup

### Prerequisites
- Python 3.8 or higher
- `pip` package manager

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd automated-posting
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 6. Configuration (.env)

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` with your API credentials:

```dotenv
# App Settings
APP_NAME="Automated Multi-Platform Posting System"
HOST=0.0.0.0
PORT=4000
DEBUG=false
REQUEST_TIMEOUT_SECONDS=10.0

# Set to true to test simulated responses without configuring live credentials:
SIMULATION_MODE=false

# Telegram Bot API
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_CHANNEL_USERNAME=

# Discord Webhook API
DISCORD_WEBHOOK_URL=
DISCORD_GUILD_ID=
DISCORD_CHANNEL_ID=
DISCORD_PUBLIC_ACCESS=false

# Mastodon API v1
MASTODON_INSTANCE_URL=mastodon.social
MASTODON_ACCESS_TOKEN=

# Twitter / X API v2
TWITTER_BEARER_TOKEN=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=

# Slack Webhook / Web API
SLACK_WEBHOOK_URL=
SLACK_BOT_TOKEN=
SLACK_CHANNEL=
```

---

## 7. Running the Application

### Start the Uvicorn Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

The server will be available at:
- **API Base URL**: http://localhost:4000
- **Interactive OpenAPI Documentation (Swagger UI)**: http://localhost:4000/docs
- **ReDoc Documentation**: http://localhost:4000/redoc
- **System Health Check**: http://localhost:4000/health

---

## 8. Testing & Code Coverage

The project includes an automated test suite with **33 unit and integration tests** covering input validation, platform adapters, error simulation, and concurrency.

### Run All Tests
```bash
pytest -v
```

### Run Tests with Coverage Report
```bash
pytest --cov=app tests/
```

### Test Results Summary
```text
============================= test session starts =============================
platform win32 -- Python 3.8.10, pytest-8.2.2
collected 33 items

tests/test_platforms.py .............                                    [ 39%]
tests/test_posting.py .....                                              [ 54%]
tests/test_validation.py ...............                                 [100%]

---------- coverage: platform win32, python 3.8.10 -----------
Name                              Stmts   Miss  Cover
-----------------------------------------------------
app\__init__.py                       1      0   100%
app\config.py                        32      0   100%
app\main.py                          57     12    79%
app\platforms\__init__.py            12      0   100%
app\platforms\base.py                63      9    86%
app\platforms\discord.py             35      0   100%
app\platforms\mastodon.py            31      1    97%
app\platforms\slack.py               53      6    89%
app\platforms\telegram.py            43      1    98%
app\platforms\twitter.py             33      2    94%
app\schemas.py                       71      3    96%
app\services\__init__.py              2      0   100%
app\services\posting_service.py      32      4    88%
-----------------------------------------------------
TOTAL                               465     38    92%

============================= 33 passed in 0.61s ==============================
```

---

## 9. Fault Isolation & Concurrency

The publishing pipeline implements the following resilience patterns:
1. **Asynchronous Non-Blocking I/O**: Driven by `httpx.AsyncClient` inside `asyncio.gather`.
2. **Independent Failure Boundaries**: If Slack returns an authentication failure or Twitter encounters a rate limit, Telegram, Discord, and Mastodon will still post successfully.
3. **Structured Logging**: Every attempt, success, and error is recorded with ISO timestamps and structured error codes.

---

## 10. Submission Details

- **Technology**: Python 3.8+, FastAPI, Uvicorn, Pydantic v2, HTTPX
- **Submission Date**: November 2026
- **Contact / Recipient**: hr@chivoxai.com
- **Author**: Python Developer Candidate
