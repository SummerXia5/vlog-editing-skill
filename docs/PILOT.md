# Founder-assisted pilot kit

This is a proposed operating workflow. No invitations have been sent, customers enrolled, or payments collected.

## Interview prompts

1. Show me the last trip you filmed but have not finished editing. What stopped you?
2. Which parts do you refuse to lose: dialogue, reactions, scenery, food, hotel, route?
3. What did the last completed edit cost in your own hours or paid help?
4. Would you prefer an editable FCP project or only an MP4? On what device do you finish?
5. What must stay off camera, private, or unuploaded? Which reviews are mandatory before delivery?
6. After seeing a real sample, would you pay the stated price for the stated scope now? Record accepted/declined; do not count compliments as intent.

## Intake (per project, stored privately)

```json
{
  "project_id": "generated-id",
  "customer_id": "private-id",
  "input_minutes": null,
  "input_gib": null,
  "target_editor": "Final Cut Pro",
  "fcp_version": null,
  "aspect_ratio": null,
  "style": null,
  "must_keep": [],
  "must_remove": [],
  "dialogue_languages": [],
  "source_processing_approved": false,
  "third_party_model_processing_approved": false,
  "public_sample_approved": false,
  "training_use_approved": false,
  "retention_agreement": null,
  "quoted_scope": null,
  "quoted_price_usd": null,
  "payment_status": "not_requested"
}
```

## Cost log

Record source minutes; proxy minutes decoded; ASR/model usage; generation retries; compute time; storage/egress; active human review/edit/support minutes; revision count; price/refund; customer acceptance; actual native FCP import and relink status. Never fill unknown costs with zero. Keep infrastructure cost and human labor separate.

## Delivery checklist tied to evidence

Every delivery includes version ID, source mapping, editable project, preview checksum, supported editor/version, missing/placeholder assets and a concise revision window. Verify a full download. For footage-specific face exclusions, inspect the specified windows; do not promise global face removal without a full audit. Verify factual place names and routes from actual experience, not the itinerary alone.

## Stop / continue decision after five

Measure the proposed gates in PRODUCT.md. If demand exists but manual time is high, remain an assisted service and narrow scope. If projects cannot be imported/relinked reliably, fix delivery before acquiring more users. If people want only short social clips, re-evaluate the segment instead of assuming this long-form/FCP offer has fit.
