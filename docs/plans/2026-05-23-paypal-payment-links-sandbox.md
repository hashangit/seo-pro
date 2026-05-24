# PayPal Payment Links Sandbox Reconciliation Plan

> **For agentic workers:** This is an experiment plan, not a production billing implementation. The first goal is to prove whether PayPal Payment Links can safely reconcile a completed payment back to one internal purchase record and one user. Do not automatically grant real credits until the reconciliation path is proven from sandbox payloads.

**Goal:** Build a sandbox-only PayPal Payment Links experiment that proves whether a dynamically generated payment link can be reconciled to the correct SEO Pro user and credit purchase.

**Architecture:** The backend creates an internal pending purchase, creates a PayPal payment resource with a unique line item `product_id`, stores the returned PayPal payment resource ID and link, then receives PayPal payment notifications. The experiment logs webhook/IPN/capture/order/payment-resource payloads so we can confirm whether PayPal returns either the `product_id`, `PLB-...` payment resource ID, or another stable identifier.

**Tech Stack:** FastAPI backend, Supabase/Postgres, PayPal Payment Links and Buttons API, PayPal sandbox, PayPal REST webhooks and/or IPN, Next.js frontend only if a simple test page is useful.

---

## Current Understanding

SEO Pro sells usage credits. Current pricing is `$1 = 8 credits`, with a minimum top-up of `$8 = 64 credits`.

The existing app already has:

- `users.credits_balance` for the current user balance.
- `credit_transactions` as a ledger.
- `credit_requests` for the current manual Wise/bank-transfer flow.
- `add_credits()` and `deduct_credits()` database functions.
- A manual purchase UI at `/credits`.

The Payment Links question is narrower:

Can we create a unique PayPal Payment Link for a logged-in user and later identify that exact paid link from PayPal's server notification?

If yes, Payment Links can support automated credit fulfillment. If no, Payment Links should remain manual-review only, and production automation should use a different PayPal API.

## Research Summary

PayPal Payment Links API supports creating payment resources:

- `POST /v1/checkout/payment-resources`
- Returns a payment resource ID such as `PLB-HL9U6YXUMCGB`.
- Returns a hosted `payment_link`.
- Supports `line_items[].product_id`.
- Supports `return_url`.
- Supports `customer_notes` as buyer-facing note fields.
- Does not clearly document a merchant-set `invoice_id` field in the Payment Links API request.

PayPal docs/community indicate Pay Links can collect buyer-entered invoice/customer note fields and pass those into transaction details, email notifications, and IPN. That confirms manual reconciliation exists, but buyer-entered values are not safe enough for automatic credits.

The strongest automation candidate is:

- Generate a unique internal purchase ID in SEO Pro.
- Send that ID to PayPal as `line_items[].product_id`.
- Store `purchase_id -> user_id -> credits -> amount -> paypal_payment_resource_id`.
- Confirm whether PayPal sends that `product_id` back in webhook/IPN/capture/order/transaction details.

## Decision We Need From Sandbox

The sandbox experiment must answer these questions with real captured payloads:

1. Does `PAYMENT.CAPTURE.COMPLETED` include the Payment Link resource ID, such as `PLB-...`?
2. Does `PAYMENT.CAPTURE.COMPLETED` include the dynamic `line_items[].product_id`?
3. If the webhook includes an order ID, does `GET /v2/checkout/orders/{order_id}` include the dynamic `product_id`?
4. Does `GET /v2/payments/captures/{capture_id}` include the dynamic `product_id`, invoice-like data, or a link back to the original Payment Link?
5. Does `GET /v1/checkout/payment-resources/{payment_resource_id}` change after payment in a way that reveals payment completion or related transaction IDs?
6. If REST webhooks do not include enough context, does IPN include `product_id`, item number, invoice ID, custom field, or another useful field for Payment Link purchases?

## Strategy

Use Payment Links only as a hosted payment page. Treat SEO Pro's database as the source of truth.

For the experiment:

1. Create an internal `paypal_payment_link_experiments` table or equivalent sandbox table.
2. Each test purchase gets a unique `purchase_id`.
3. Create a PayPal payment resource with:

```json
{
  "integration_mode": "LINK",
  "type": "BUY_NOW",
  "reusable": "MULTIPLE",
  "return_url": "https://<public-app-url>/credits/paypal/return?purchase_id=<opaque_purchase_id>",
  "line_items": [
    {
      "name": "SEO Pro 160 Credits",
      "product_id": "<opaque_purchase_id>",
      "description": "Sandbox credit purchase reconciliation test",
      "unit_amount": {
        "currency_code": "USD",
        "value": "20.00"
      }
    }
  ]
}
```

4. Store PayPal's response, including `id`, `payment_link`, and full JSON.
5. Complete the payment with a PayPal sandbox buyer account.
6. Capture every notification and follow-up API response raw.
7. Decide whether Payment Links are safe enough for automated credit fulfillment.

Do not use the `return_url` as proof of payment. The return URL is only UX. Server-side PayPal verification is required.

## Integrity Rules

These rules apply if the experiment later becomes production:

- Never grant credits from the browser return URL alone.
- Never trust the client-provided amount or credit count.
- Server must calculate credits and amount from SEO Pro pricing.
- A completed PayPal event must map to exactly one pending internal purchase.
- The purchase must belong to exactly one user.
- The paid currency and gross amount must match the pending purchase.
- PayPal event IDs and capture IDs must be idempotent.
- Credit fulfillment must be one atomic database operation.
- If reconciliation is ambiguous, do not grant credits automatically; mark the purchase for admin review.

## Proposed Sandbox Files

Backend:

- Create `api/services/paypal.py`
  - OAuth token retrieval.
  - Create payment resource.
  - Verify webhook signature if using REST webhooks.
  - Fetch capture/order/payment-resource details.

- Create `api/routes/paypal_sandbox.py`
  - `POST /api/v1/sandbox/paypal/payment-link`
  - `POST /api/v1/sandbox/paypal/webhook`
  - `POST /api/v1/sandbox/paypal/ipn`
  - `GET /api/v1/sandbox/paypal/experiments/{purchase_id}`

- Create `api/models/paypal.py`
  - Request/response models for the sandbox experiment.

- Create `supabase/migrations/003_paypal_payment_link_sandbox.sql`
  - Sandbox experiment table.
  - Raw notification table.

Frontend, optional:

- Create `frontend/app/credits/paypal-sandbox/page.tsx`
  - Authenticated test UI for choosing a credit amount and opening the returned PayPal link.

- Create `frontend/app/credits/paypal/return/page.tsx`
  - Shows "payment return received" and tells the user to wait for server confirmation.

Tests:

- Create `api/tests/test_paypal_sandbox.py`
  - Unit tests for amount calculation, payload construction, idempotency checks, and webhook logging.

## Environment Variables

Add sandbox-only settings:

```text
SEO_PRO_PAYPAL_CLIENT_ID=
SEO_PRO_PAYPAL_CLIENT_SECRET=
SEO_PRO_PAYPAL_ENVIRONMENT=sandbox
SEO_PRO_PAYPAL_WEBHOOK_ID=
SEO_PRO_PAYPAL_ENABLE_SANDBOX_ROUTES=true
SEO_PRO_PUBLIC_WEBHOOK_BASE_URL=
```

Sandbox routes must be disabled in production unless explicitly enabled for testing.

## Database Sketch

Use separate sandbox tables so the experiment cannot accidentally affect real credit balances.

```sql
CREATE TABLE IF NOT EXISTS paypal_payment_link_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purchase_id TEXT UNIQUE NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0),
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    paypal_payment_resource_id TEXT,
    paypal_payment_link TEXT,
    status TEXT NOT NULL DEFAULT 'created'
        CHECK (status IN ('created', 'link_created', 'returned', 'webhook_received', 'reconciled', 'unmatched', 'failed')),
    reconciliation_result JSONB DEFAULT '{}'::jsonb,
    create_response JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paypal_payment_link_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paypal_event_id TEXT,
    event_type TEXT,
    purchase_id TEXT,
    paypal_capture_id TEXT,
    paypal_order_id TEXT,
    paypal_payment_resource_id TEXT,
    source TEXT NOT NULL CHECK (source IN ('rest_webhook', 'ipn', 'manual_fetch')),
    headers JSONB DEFAULT '{}'::jsonb,
    payload JSONB NOT NULL,
    related_api_responses JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Implementation Tasks

### Task 1: Add Sandbox Configuration

**Files:**

- Modify `api/config.py`

Add PayPal settings to both `Settings` classes:

```python
PAYPAL_CLIENT_ID: str | None = Field(default=None, description="PayPal REST app client ID")
PAYPAL_CLIENT_SECRET: str | None = Field(default=None, description="PayPal REST app client secret")
PAYPAL_ENVIRONMENT: Literal["sandbox", "production"] = Field(default="sandbox", description="PayPal environment")
PAYPAL_WEBHOOK_ID: str | None = Field(default=None, description="PayPal REST webhook ID")
PAYPAL_ENABLE_SANDBOX_ROUTES: bool = Field(default=False, description="Enable sandbox-only PayPal test routes")
PUBLIC_WEBHOOK_BASE_URL: str | None = Field(default=None, description="Public URL for PayPal webhook callbacks")
```

Acceptance:

- App starts without PayPal env vars.
- Sandbox routes check `PAYPAL_ENABLE_SANDBOX_ROUTES` before doing anything.

### Task 2: Add Sandbox Tables

**Files:**

- Create `supabase/migrations/003_paypal_payment_link_sandbox.sql`

Implement the two tables from the database sketch.

Acceptance:

- Migration creates tables without changing real credit behavior.
- Tables store raw JSON payloads for later inspection.

### Task 3: Create PayPal Service

**Files:**

- Create `api/services/paypal.py`

Implement:

- `get_paypal_base_url(settings) -> str`
- `get_paypal_access_token(settings) -> str`
- `create_payment_resource(settings, purchase_id, credits, amount, currency, return_url) -> dict`
- `verify_paypal_webhook_signature(settings, headers, payload) -> bool`
- `fetch_paypal_capture(settings, capture_id) -> dict`
- `fetch_paypal_order(settings, order_id) -> dict`
- `fetch_payment_resource(settings, payment_resource_id) -> dict`

Create payment resource payload with dynamic `product_id = purchase_id`.

Acceptance:

- Unit test verifies the create payload contains the exact `purchase_id` as `line_items[0].product_id`.
- Unit test verifies sandbox base URL is `https://api-m.sandbox.paypal.com`.

### Task 4: Create Sandbox Routes

**Files:**

- Create `api/routes/paypal_sandbox.py`
- Modify `api/main.py` to include the router only when sandbox routes are enabled.

Routes:

- `POST /api/v1/sandbox/paypal/payment-link`
  - Auth required.
  - Input: `credits`.
  - Validate minimum 64 credits and multiples of 8.
  - Calculate amount as `credits / 8`.
  - Create internal `purchase_id`, for example `seo_pro_<uuid>`.
  - Insert experiment row.
  - Create PayPal payment resource.
  - Update row with PayPal resource ID and link.
  - Return `purchase_id`, `payment_resource_id`, and `payment_link`.

- `POST /api/v1/sandbox/paypal/webhook`
  - No app auth.
  - Verify PayPal webhook signature when `PAYPAL_WEBHOOK_ID` is configured.
  - Store raw headers and body.
  - For `PAYMENT.CAPTURE.COMPLETED`, extract capture ID, amount, currency, order ID if present.
  - Fetch capture/order details if possible.
  - Search all payloads for the internal `purchase_id`, `product_id`, or `PLB-...` ID.
  - Store reconciliation result.
  - Do not call `add_credits()`.

- `POST /api/v1/sandbox/paypal/ipn`
  - Store raw form payload.
  - Verify IPN with PayPal if implemented.
  - Search payload for `purchase_id`, `product_id`, item number/name, invoice-like fields.
  - Store reconciliation result.
  - Do not call `add_credits()`.

- `GET /api/v1/sandbox/paypal/experiments/{purchase_id}`
  - Auth required.
  - Only returns rows owned by the current user.
  - Returns experiment row and related notifications.

Acceptance:

- The webhook endpoint persists the raw payload even when reconciliation fails.
- The webhook endpoint returns `200 OK` quickly after storing payloads.
- No route can mutate `users.credits_balance`.

### Task 5: Optional Test UI

**Files:**

- Create `frontend/app/credits/paypal-sandbox/page.tsx`
- Create `frontend/app/credits/paypal/return/page.tsx`
- Add client functions to `frontend/lib/api.ts`

UI behavior:

- User selects one of: 64, 160, 400 credits.
- Button calls sandbox backend endpoint.
- UI displays `purchase_id`, `payment_resource_id`, and `payment_link`.
- User clicks the PayPal link.
- Return page displays the `purchase_id` from the query string and polls the experiment details endpoint.

Acceptance:

- UI is clearly labeled as sandbox/testing only.
- UI does not display "credits added" unless a future production fulfillment path exists.

### Task 6: Run Sandbox Experiment

**Manual Steps:**

1. Create or use an existing PayPal sandbox REST app.
2. Enable Payment Links and Buttons for that app if required.
3. Set env vars.
4. Expose local backend using a public HTTPS tunnel or deploy to a staging URL.
5. Register PayPal REST webhook for payment capture events.
6. Create a test link from the SEO Pro sandbox UI/API.
7. Pay using a PayPal sandbox buyer.
8. Inspect stored rows in:
   - `paypal_payment_link_experiments`
   - `paypal_payment_link_notifications`
9. Manually fetch related capture/order/payment-resource details if needed and store them.

Acceptance:

- Produce one written result in `docs/research/paypal-payment-links-sandbox-result.md`.
- Include the sanitized create-payment-resource response.
- Include sanitized webhook/IPN payloads.
- Include sanitized capture/order/payment-resource fetch responses.
- State whether `purchase_id`, `product_id`, or `PLB-...` appears in any server-verified payment data.

## Success Criteria

Payment Links are considered safe for automated credits only if all are true:

- PayPal server-side data includes our internal purchase ID or the PayPal payment resource ID.
- That identifier can be extracted without relying on user-entered text.
- Paid amount and currency can be verified.
- PayPal event/capture can be made idempotent.
- The internal purchase can be fulfilled atomically.

If these are not true, do not use Payment Links for automatic crediting.

## Production Follow-Up If Sandbox Succeeds

If the experiment succeeds, build a production payment subsystem:

- Rename sandbox tables to production-grade `payment_purchases` and `payment_notifications`, or create fresh production migrations.
- Add a DB function such as `fulfill_credit_purchase()` that locks the purchase row, verifies unfulfilled status, updates user balance, writes ledger, and marks fulfilled in one transaction.
- Update `/credits` UI to redirect to PayPal.
- Keep manual credit requests as admin fallback.
- Add admin monitoring for unmatched/failed payments.
- Add tests for idempotency, mismatched amount, wrong currency, duplicate webhook, and ambiguous reconciliation.

## Production Follow-Up If Sandbox Fails

If Payment Links do not return a stable identifier:

- Do not implement automated fulfillment with Payment Links.
- Keep Payment Links manual-review only, using invoice/customer note data.
- For automated credit delivery, use a PayPal API that supports merchant-controlled reconciliation fields such as `custom_id` or `invoice_id`.

## Useful Sources

- PayPal Payment Links API: https://docs.paypal.ai/payments/pay-links-buttons-api
- PayPal create payment link docs: https://docs.paypal.ai/payments/create-pay-link
- PayPal community thread on Pay Links invoice/customer note details and IPN: https://www.paypal-community.com/t5/PayPal-Payments-Standard/Simple-easy-Checkout-integration-for-me-website/td-p/3150201
- PayPal webhook verification: https://developer.paypal.com/docs/api/webhooks/v1/
- PayPal Payments Captures API: https://developer.paypal.com/docs/api/payments/v2/
