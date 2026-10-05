# O'zgarishlar tarixi

## 1.0 — 2026-10-05

Birinchi versiya.

- Hodisa konverti: `event_id` (idempotentlik), `supersedes` (tuzatish),
  `organization.stir`, `site_id`.
- Hodisa turlari: `site.profile`, `site.status`, `site.work_plan`,
  `site.daily_report`, `site.photo`, `site.incident`.
- API: `POST /v1/events` (1–500 hodisa), `POST /v1/media`, `GET /v1/ping`.
- HMAC-SHA256 imzo, 300 soniyalik vaqt chegarasi.
- Python kutubxonasi: `hodisa_xatolari`, `sign_request`, `imzoni_tekshir`.
