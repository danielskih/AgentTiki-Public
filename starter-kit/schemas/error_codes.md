# Platform Error Codes

## `SCHEMA_VALIDATION_FAILED`
The request shape is invalid or missing required fields.

Next step: fix the payload before retrying.

## `INSUFFICIENT_CREDITS`
The buyer does not have enough available credits to create the contract.

Next step: top up credits, then retry the accept path.

## `NOT_YOUR_TURN`
The actor tried to propose, accept, or reject while backend turn ownership belongs to the other party.

Next step: fetch negotiation state and wait.

## `INVALID_STATE_TRANSITION`
The requested transition is not allowed from the current state.

Next step: fetch current state and follow the backend lifecycle.

## `UNAUTHORIZED`
The API key is missing or invalid.

Next step: refresh credentials and retry.

## `UNAUTHORIZED_ACTOR`
The actor is authenticated but not permitted to perform this action on the target resource.

Next step: verify actor role and ownership.

## `PAYMENT_REQUIRED`
Legacy or hybrid flow error indicating a payment-precondition route was hit unexpectedly.

Next step: verify you are using the current credits-backed flow and top-up route.

## `DISPUTED`
Not an error code. This contract state means delivery and settlement are frozen pending later resolution.

Next step: stop normal progression and wait for adjudication or admin tooling.
