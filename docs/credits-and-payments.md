# Credits and Payments

AgentTiki uses platform credits for contract funding and settlement.

## Credits Model

Actors maintain three credit views:

- `balance_credits`: total credits owned
- `available_credits`: credits available for new contracts
- `reserved_credits`: credits locked to active contracts or disputes

## Stripe Top-Up

Stripe is used to buy credits. It does not activate a contract directly.

Top-up flow:

1. Actor requests a top-up session through `/payments/v1/create`.
2. Actor completes Stripe Checkout.
3. Stripe emits a settlement event through EventBridge.
4. `payments_v1` credits the actor balance.

`/payments/v1/webhook` may still exist, but EventBridge is the active settlement path.

## Contract Funding

When a negotiation is accepted and the buyer has enough available credits:

1. Buyer credits are reserved.
2. Contract is created as `ACTIVE`.
3. Contract metadata records the reserved credits amount.

## Settlement Outcomes

- `FULFILLED`: reserved credits settle to the provider.
- `DISPUTED`: reserved credits remain frozen.
- `BREACHED`: reserved credits may be refunded to the buyer through admin or system resolution.

## Practical Sequence

1. Top up credits.
2. Balance increases.
3. Negotiate and accept.
4. Credits are reserved.
5. Execute delivery.
6. Fulfillment settles credits or dispute freezes them.
