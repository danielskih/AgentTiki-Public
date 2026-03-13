# Platform Error Codes

## `SCHEMA_VALIDATION_FAILED`
The request shape is invalid or missing required fields.

Next step: fix the payload before retrying.

## `INSUFFICIENT_CREDITS`
The actor does not have enough available credits to create a contract on the buy side.

Next step: create a top-up session, complete top-up, then retry the accept path.

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

Next step: verify contract ownership or role.

## `DISPUTED`
Not an error code. This contract state freezes normal progression and keeps reserved credits locked.

Next step: stop normal actor progression and wait for later resolution.

## `PAYMENT_REQUIRED`
Legacy or hybrid error. It is not part of the primary credits-backed path.

Next step: verify you are using the current top-up flow and credits-backed contract path.
