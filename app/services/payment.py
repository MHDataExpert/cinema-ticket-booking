def process_payment(payment_token: str) -> bool:
    # TODO: replace with real Stripe webhook (stripe.PaymentIntent + webhook signature verify).
    return payment_token != "fail"
